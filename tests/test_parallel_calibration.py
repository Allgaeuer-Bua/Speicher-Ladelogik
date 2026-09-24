"""Exercise the two-session planner with realistic independent device states."""

from datetime import datetime, timezone
from enum import Enum
from importlib import import_module
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
import sys


ROOT = Path(__file__).parents[1] / "custom_components" / "speicher_ladelogik"
_package = ModuleType("calibration_fixture")
_package.__path__ = [str(ROOT)]
_ha = ModuleType("homeassistant")
_core = ModuleType("homeassistant.core")
_core.HomeAssistant = object
_util = ModuleType("homeassistant.util")
_dt = ModuleType("homeassistant.util.dt")
_dt.as_timestamp = lambda value: value.timestamp() if hasattr(value, "timestamp") else float(value)
_dt.parse_datetime = datetime.fromisoformat
_const = ModuleType("homeassistant.const")
_const.Platform = Enum("Platform", "SENSOR SWITCH SELECT NUMBER BUTTON")
with patch.dict(sys.modules, {
    "calibration_fixture": _package, "homeassistant": _ha,
    "homeassistant.core": _core, "homeassistant.util": _util,
    "homeassistant.util.dt": _dt, "homeassistant.const": _const,
}):
    planner = import_module("calibration_fixture.planner")
    persistence = import_module("calibration_fixture.persistence")


DAY = datetime(2026, 9, 24, tzinfo=timezone.utc).timestamp()
NOW = DAY + 7 * 3600


class States:
    def __init__(self, states):
        self.states = states

    def get(self, key):
        return self.states.get(key)


def state(value, now, unit=None, **attributes):
    if unit:
        attributes["unit_of_measurement"] = unit
    return SimpleNamespace(state=str(value), attributes=attributes,
                           last_reported=datetime.fromtimestamp(now, timezone.utc))


def scenario(*, pv=3000, live_load=1000, secondary_phase="wait", primary_phase="charge"):
    """A and E each sit near 13 %, with a ready PV forecast."""
    now = NOW
    states = {}

    def add(key, value, unit=None, **attrs):
        states[key] = state(value, now, unit, **attrs)

    for day, suffix in ((DAY, "today"), (DAY + 86400, "tomorrow")):
        buckets = {datetime.fromtimestamp(day + index * 900, timezone.utc).isoformat(): 350
                   for index in range(96)}
        for direction in ("sw", "so", "no"):
            add(f"sensor.{direction}_energy_production_{suffix}", 33.6, "kWh", wh_period_15m=buckets)
    add("sensor.aktuelle_pv_leistung", pv, "W")
    add("sensor.stromzahler_leistung", -1500, "W")
    add("sensor.hausleistung_gesamt", live_load, "W")
    add("sensor.hausleistung_gesamt_30_min", 1000, "W")
    add("sensor.pv_produktion_tag", 30, "kWh")
    add("sun.sun", "above_horizon")
    add("input_select.speicher_ladelogik_betriebsart", "Automatik")
    add("input_boolean.speicher_ladelogik_aktiv", "on")
    add("input_text.speicher_ladelogik_sicherung", "backup2|0|-1|0|1500|-1|2500")
    add("input_text.speicher_ladelogik_kalibrierung_sicherung", "backup2|0|-1|0|1500|-1|2500")
    add("input_text.speicher_ladelogik_kalibrierung_vormerkungen", "")
    add("input_boolean.speicher_ladelogik_kalibrierung_a_freigegeben", "on")
    add("input_boolean.speicher_ladelogik_kalibrierung_e_freigegeben", "on")
    add("sensor.speicher_ladelogik_lernspeicher", "bereit", active={}, history=[], models={})
    for key, soc, power in (("a", 12, -500 if primary_phase == "charge" else 0), ("e", 12, 0)):
        prefix = f"marstek_venus_{key}"
        add(f"sensor.{prefix}_soc" + ("_batterie" if key == "a" else ""), soc, "%")
        add(f"sensor.{prefix}_ac_leistung", power, "W")
        add(f"switch.astrameter_venus_{key}_auto_target", "on")
        add(f"switch.astrameter_venus_{key}_active", "on")
        add(f"input_boolean.venus_{key}_nicht_laden", "off")
        add(f"sensor.{prefix}_maximale_zellentemperatur" if key == "a" else f"sensor.{prefix}_max_zelltemperatur", 25, "°C")
        add(f"sensor.{prefix}_minimale_zellentemperatur" if key == "a" else f"sensor.{prefix}_min_zelltemperatur", 24, "°C")
        add(f"sensor.{prefix}_maximale_zellenspannung" if key == "a" else f"sensor.{prefix}_max_zellspannung", 3.35, "V")
        add(f"number.{prefix}_maximaler_soc" if key == "a" else f"number.{prefix}_obere_ladegrenze_kapazitat", 100)
        add(f"number.{prefix}_minimaler_soc" if key == "a" else f"number.{prefix}_untere_ladegrenze_kapazitat", 12)
        charge = f"number.{prefix}_maximale_ladeleistung" if key == "a" else f"number.{prefix}_ladeleistung"
        discharge = f"number.{prefix}_maximale_entladeleistung" if key == "a" else f"number.{prefix}_entladeleistung"
        add(charge, 500 if key == "a" else 0, min=0, max=1500 if key == "a" else 2500, step=50)
        add(discharge, 0, min=0, max=1500 if key == "a" else 2500, step=50)
    for pack in (1, 2):
        add(f"sensor.marstek_venus_a_soc_batteriepack_{pack}", 12, "%")
    for key, phase in (("A", primary_phase), ("E", secondary_phase)):
        session = persistence.read_session("")
        session.update({"p": phase, "b": key, "t": now - 100,
                        "s": now - 600, "x": now + 12 * 3600,
                        "n": DAY, "q": now - 15, "z": 2 if key == "A" else 1,
                        "h": int(phase == "charge")})
        if key == "A":
            add("input_text.speicher_ladelogik_kalibrierung_sitzung", persistence.encode_session(session))
        else:
            secondary = persistence.encode_session(session)
    payload = {"battery_keys": ["A", "E"], "parallel_calibration": True,
               "parallel_session": secondary, "now": now, "day0": DAY,
               "day1": DAY + 86400, "day2": DAY + 172800,
               "nine": DAY + 9 * 3600, "eleven": DAY + 11 * 3600,
               "deadline": DAY + 18 * 3600, "midday_start": DAY + 9 * 3600,
               "midday_end": DAY + 18 * 3600}
    return SimpleNamespace(states=States(states)), payload


def test_second_charge_requires_shared_pv_surplus():
    with patch.dict(sys.modules, {"homeassistant": _ha, "homeassistant.core": _core,
                                  "homeassistant.util": _util, "homeassistant.util.dt": _dt}):
        hass, payload = scenario(live_load=2600)
        low = planner.calculate_plan(hass, payload)
        assert persistence.read_session(low["parallel_session"])["p"] == "wait"
        hass, payload = scenario(pv=3000)
        enough = planner.calculate_plan(hass, payload)
        assert persistence.read_session(enough["parallel_session"])["p"] == "charge"
        assert enough["plan"]["kalibrier_reserviert_w"] == 1000
        limits = {command["battery"]: command["value"] for command in enough["proposed_commands"]
                  if not command["restore"] and "ladeleistung" in command["entity"]}
        assert limits.get("E") == 500


def test_prepared_second_storage_gets_an_independent_session():
    with patch.dict(sys.modules, {"homeassistant": _ha, "homeassistant.core": _core,
                                  "homeassistant.util": _util, "homeassistant.util.dt": _dt}):
        hass, payload = scenario(primary_phase="wait", secondary_phase="idle")
        hass.states.states["input_text.speicher_ladelogik_kalibrierung_vormerkungen"] = state(
            f"queue1|E,{int(DAY)},{int(NOW)},-", NOW)
        result = planner.calculate_plan(hass, payload)
        assert persistence.read_session(result["session"])["b"] == "A"
        secondary = persistence.read_session(result["parallel_session"])
        assert secondary["b"] == "E" and secondary["p"] == "empty_rest"
        assert len(result["calibration"]["laufende_laeufe"]) == 2


def test_independent_finished_runs_keep_both_results():
    with patch.dict(sys.modules, {"homeassistant": _ha, "homeassistant.core": _core,
                                  "homeassistant.util": _util, "homeassistant.util.dt": _dt}):
        hass, payload = scenario(secondary_phase="full_rest", primary_phase="full_rest")
        payload["parallel_calibration"] = False  # disabling the option must not discard running jobs
        sessions = []
        for encoded in (hass.states.states["input_text.speicher_ladelogik_kalibrierung_sitzung"].state,
                        payload["parallel_session"]):
            item = persistence.read_session(encoded)
            item["f"] = NOW - 90 * 60
            item["t"] = NOW - 100 * 60
            item["w"] = 3900 if item["b"] == "A" else 5150
            sessions.append(persistence.encode_session(item))
        hass.states.states["input_text.speicher_ladelogik_kalibrierung_sitzung"] = state(sessions[0], NOW)
        payload["parallel_session"] = sessions[1]
        hass.states.states["input_text.speicher_ladelogik_kalibrierung_sicherung"] = state(
            "backup2|-1|-1|-1|-1|-1|-1", NOW)
        for key in ("a", "e"):
            soc = f"sensor.marstek_venus_{key}_soc" + ("_batterie" if key == "a" else "")
            hass.states.states[soc] = state(100, NOW, "%")
            hass.states.states[f"sensor.marstek_venus_{key}_ac_leistung"] = state(0, NOW, "W")
        for pack in (1, 2):
            hass.states.states[f"sensor.marstek_venus_a_soc_batteriepack_{pack}"] = state(100, NOW, "%")
        out = planner.calculate_plan(hass, payload)
        assert {item["battery"] for item in out["finish_events"]} == {"A", "E"}
        assert all(item["capture_drift"] for item in out["finish_events"])
        assert out["parallel_session"] == ""
        assert {record["battery"] for record in out["learning"]["history"]} == {"A", "E"}


def test_full_soc_drift_baseline_is_recorded_at_start_of_upper_rest():
    with patch.dict(sys.modules, {"homeassistant": _ha, "homeassistant.core": _core,
                                  "homeassistant.util": _util, "homeassistant.util.dt": _dt}):
        hass, payload = scenario(secondary_phase="idle")
        primary = persistence.read_session(
            hass.states.states["input_text.speicher_ladelogik_kalibrierung_sitzung"].state)
        primary["f"] = NOW - 61
        hass.states.states["input_text.speicher_ladelogik_kalibrierung_sitzung"] = state(
            persistence.encode_session(primary), NOW)
        hass.states.states["sensor.marstek_venus_a_soc_batterie"] = state(100, NOW, "%")
        for pack in (1, 2):
            hass.states.states[f"sensor.marstek_venus_a_soc_batteriepack_{pack}"] = state(100, NOW, "%")
            hass.states.states[f"sensor.venus_a_pack_{pack}_zelldrift"] = state(11 + pack, NOW, "mV")
        hass.states.states["sensor.speicher_ladelogik_lernspeicher"] = state(
            "bereit", NOW, active_runs={"A": {"battery": "A", "start": NOW - 3000,
              "soc": 12, "usable_reference": 3.6608, "eta": 0.9}},
            active={}, history=[], models={})
        out = planner.calculate_plan(hass, payload)
        assert persistence.read_session(out["session"])["p"] == "full_rest"
        assert out["learning"]["active_runs"]["A"]["drift_top_start_mv"] == [12.0, 13.0]
