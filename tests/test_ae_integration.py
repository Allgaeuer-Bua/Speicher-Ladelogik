"""The independent A/E package must never map a battery onto the old D slot."""
from __future__ import annotations

import importlib.util
import sys
import types
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parents[1] / "custom_components" / "speicher_ladelogik_ae"
spec = importlib.util.spec_from_file_location("ae_scenario", Path(__file__).with_name("ae_fixture.py"))
fx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fx)
fx._dt.utcnow = lambda: datetime.fromtimestamp(fx.NOW, timezone.utc)
package = types.ModuleType("ae_fixture")
package.__path__ = [str(ROOT)]
stubs = {
    "ae_fixture": package, "homeassistant": fx._ha,
    "homeassistant.core": fx._core, "homeassistant.util": fx._util,
    "homeassistant.util.dt": fx._dt, "homeassistant.const": fx._const,
}
with patch.dict(sys.modules, stubs):
    const = import_module("ae_fixture.const")
    storage = import_module("ae_fixture.storage")
    stability = import_module("ae_fixture.stability")
    planner = import_module("ae_fixture.planner")
    runtime = import_module("ae_fixture.runtime")


def test_ae_configuration_has_only_two_models_and_keeps_optional_a_mppts():
    config = {
        **const.DEFAULTS,
        "storage_instances": [
            {"id": "a", "name": "Venus A", "model": "A", "modules": 2,
             "mppt_sensors": [f"sensor.venus_a_mppt_{i}" for i in range(1, 5)]},
            {"id": "e", "name": "Venus E", "model": "E", "modules": 1},
            {"id": "d", "name": "Venus D", "model": "D", "modules": 2},
        ],
    }
    normalized, instances = storage.normalize_config(config)
    assert [item["model"] for item in instances] == ["A", "E"]
    assert normalized["enabled_models"] == ["A", "E"]
    assert normalized["a_mppt_sensors"] == [f"sensor.venus_a_mppt_{i}" for i in range(1, 5)]
    assert normalized["slot_models"] == {"A": "A", "E": "E"}


def test_default_sources_never_require_venus_d():
    assert all("venus_d" not in str(value) for value in const.DEFAULTS.values())
    assert all(not str(key).startswith("d_") for key in const.DEFAULTS)
    assert const.CONF_A_MIN_SOC not in const.DEFAULTS


def test_last_percent_keeps_register_on_forecast_pause_but_safety_stop_wins():
    base = dict(raw_limit=0, previous_limit=1100, current_cap=1500,
                eligible=True, target_reached=False, within_window=False,
                planner_status="Platz für Mittagsspitze halten", safety_stop=False,
                decision_locked=True, slot_was_active=False,
                final_percent_pending=True, actual_limit=1100, preferred_limit=1100)
    assert stability.stable_charge_limit(**base) == (
        1100, True, "Letztes SoC-Prozent: Ladegrenze beibehalten")
    assert stability.stable_charge_limit(**{**base, "safety_stop": True})[0] == 0
    assert stability.stable_charge_limit(**{**base, "final_percent_pending": False})[0] == 0
    assert stability.stable_charge_limit(**{**base, "previous_limit": 0})[0] == 1100


def test_full_battery_uses_the_actual_register_when_prior_plan_is_stale():
    value, held, _ = stability.stable_charge_limit(
        raw_limit=0, previous_limit=0, current_cap=1500,
        eligible=True, target_reached=True, within_window=False,
        planner_status="Ziel erreicht", safety_stop=False, actual_limit=1100)
    assert (value, held) == (1100, True)


def test_venus_a_near_full_keeps_register_in_real_peak_planner():
    hass, payload = fx.scenario(primary_phase="idle", secondary_phase="idle", pv=14390, live_load=278)
    payload.update(midday_start=fx.NOW - 3600, midday_end=fx.NOW + 9000,
                   solar_noon=fx.NOW + 3600, nine=fx.NOW - 7200, eleven=fx.NOW - 3600)
    for key in ("sensor.marstek_venus_a_soc_batterie", "sensor.marstek_venus_a_soc_batteriepack_1",
                "sensor.marstek_venus_a_soc_batteriepack_2"):
        hass.states.states[key] = fx.state(99, fx.NOW, "%")
    hass.states.states["sensor.marstek_venus_e_soc"] = fx.state(100, fx.NOW, "%")
    for direction in ("sw", "so", "no"):
        entity = f"sensor.{direction}_energy_production_today"
        buckets = {
            datetime.fromtimestamp(fx.DAY + index * 900, timezone.utc).isoformat():
            (130 if index <= 28 else 1200 if index < 48 else 100)
            for index in range(96)
        }
        hass.states.states[entity] = fx.state(30, fx.NOW, unit="kWh", wh_period_15m=buckets)
    controls = dict(runtime.CONTROL_DEFAULTS)
    controls.update(mode="Automatik", bevorzugte_ladeleistung_a_w=1100)
    with patch.dict(sys.modules, stubs):
        hass.states.states.update(runtime.planner_states(controls))
        payload["prior_plan"] = {
            "version": "2.0.2", "berechnet_ts": fx.NOW - 20,
            "betriebsart": "Automatik", "regelung_aktiv": True,
            "daten_gueltig": True, "mittagsspitzen_aktiv": True,
            "fahrplan_slot_start_ts": int(fx.NOW // 900) * 900,
            "fahrplan_slot_aktiv_venus_a": False,
            "fahrplan_ladegrenze_stabil_venus_a_w": 1100,
        }
        plan = planner.calculate_plan(hass, payload)["plan"]
    assert plan["fahrplan_ladegrenze_roh_venus_a_w"] == 0
    assert plan["soll_ladegrenze_venus_a_w"] == 1100
    assert plan["fahrplan_slot_aktiv_venus_a"] is False
    assert plan["soll_ladeleistung_gesamt_w"] == 0


def _waiting_venus_e(*, phase="wait", soc=13, pause_minutes=45, earliest=None):
    hass, payload = fx.scenario(primary_phase="idle", secondary_phase="idle",
                                pv=3000, live_load=126)
    hass.states.states["sensor.marstek_venus_e_soc"] = fx.state(soc, fx.NOW, "%")
    session = fx.persistence.read_session("")
    session.update(p=phase, b="E", t=fx.NOW - pause_minutes * 60,
                   s=fx.NOW - 900, x=fx.NOW + 12 * 3600,
                   n=earliest if earliest is not None else fx.DAY, z=1,
                   r="waiting_pv" if phase == "wait" else "empty_resting")
    controls = dict(runtime.CONTROL_DEFAULTS)
    controls.update(mode="Automatik", kalibrierung_e_freigegeben=True,
                    kalibrierleistung_w=550, kalibrierung_ruhe_unten_min=pause_minutes,
                    kalibrierung_sicherung="backup2|0|-1|0|1500|-1|2500",
                    kalibrierung_sitzung=fx.persistence.encode_session(session))
    with patch.dict(sys.modules, stubs):
        hass.states.states.update(runtime.planner_states(controls))
    return hass, payload


def test_today_button_retimes_waiting_tomorrow_calibration_and_starts_with_live_pv():
    hass, payload = _waiting_venus_e(earliest=fx.DAY + 86400)
    with patch.dict(sys.modules, stubs):
        before = planner.calculate_plan(hass, payload)
        payload["request"] = "cal_e"
        after = planner.calculate_plan(hass, payload)
    assert before["calibration"]["phase"] == "wait"
    assert before["calibration"]["auftraege"][0]["fruehestens_ts"] == fx.DAY + 86400
    assert before["calibration"]["heute_e"]["ok"] is True
    assert after["calibration"]["phase"] == "charge"
    assert after["calibration"]["auftraege"][0]["fruehestens_ts"] == fx.DAY
    assert after["calibration"]["leistung_w"] == 550


def test_empty_rest_does_not_restart_after_one_percent_soc_rebound():
    hass, payload = _waiting_venus_e(phase="empty_rest", soc=14)
    with patch.dict(sys.modules, stubs):
        result = planner.calculate_plan(hass, payload)
    assert result["calibration"]["phase"] == "wait"
    assert result["calibration"]["heute_e"]["ok"] is True


def test_started_wait_window_can_charge_with_live_surplus_after_forecast_moves():
    hass, payload = _waiting_venus_e()
    for direction in ("sw", "so", "no"):
        key = f"sensor.{direction}_energy_production_today"
        buckets = {
            datetime.fromtimestamp(fx.DAY + index * 900, timezone.utc).isoformat():
            (350 if index < 30 else 0)
            for index in range(96)
        }
        hass.states.states[key] = fx.state(20, fx.NOW, unit="kWh", wh_period_15m=buckets)
    with patch.dict(sys.modules, stubs):
        result = planner.calculate_plan(hass, payload)
    assert result["calibration"]["heute_e"]["ok"] is False
    assert result["calibration"]["phase"] == "charge"


def test_booked_window_still_requires_live_surplus_and_empty_battery():
    for soc, pv in ((13, 150), (15, 3000)):
        hass, payload = _waiting_venus_e(soc=soc)
        hass.states.states["sensor.aktuelle_pv_leistung"] = fx.state(pv, fx.NOW, "W")
        with patch.dict(sys.modules, stubs):
            result = planner.calculate_plan(hass, payload)
        assert result["calibration"]["phase"] != "charge"


def test_today_request_during_register_restore_is_queued_for_after_restore():
    hass, payload = _waiting_venus_e(phase="restore", earliest=fx.DAY + 86400)
    payload["request"] = "cal_e"
    with patch.dict(sys.modules, stubs):
        result = planner.calculate_plan(hass, payload)
    assert result["calibration"]["vormerkungen"][0]["batterie"] == "E"
    assert result["calibration"]["vormerkungen"][0]["fruehestens_ts"] == fx.DAY


def test_marginal_forecast_waits_then_starts_on_live_surplus_instead_of_retrying_tomorrow():
    hass, payload = _waiting_venus_e(phase="empty_rest", pause_minutes=45)
    for direction in ("sw", "so", "no"):
        key = f"sensor.{direction}_energy_production_today"
        buckets = {
            datetime.fromtimestamp(fx.DAY + index * 900, timezone.utc).isoformat():
            (350 if 28 <= index < 64 else 0)
            for index in range(96)
        }
        hass.states.states[key] = fx.state(30, fx.NOW, unit="kWh", wh_period_15m=buckets)
    with patch.dict(sys.modules, stubs):
        first = planner.calculate_plan(hass, payload)
        assert first["calibration"]["heute_e"]["ok"] is False
        assert first["calibration"]["heute_e"]["longest_h"] >= 8.86
        assert first["calibration"]["phase"] == "wait"
        hass.states.states["input_text.speicher_ladelogik_ae_kalibrierung_sitzung"] = fx.state(
            first["session"], fx.NOW)
        second = planner.calculate_plan(hass, payload)
    assert second["calibration"]["phase"] == "charge"
    assert second["calibration"]["auftraege"][0]["fruehestens_ts"] == fx.DAY


def test_marginal_today_window_does_not_cancel_drain_before_live_pv_can_start_charge():
    hass, payload = _waiting_venus_e(phase="drain", soc=14, pause_minutes=0)
    hass.states.states["input_number.speicher_ladelogik_ae_kalibrierleistung_w"] = fx.state(
        500, fx.NOW, "W")
    for direction in ("sw", "so", "no"):
        buckets = {
            datetime.fromtimestamp(fx.DAY + index * 900, timezone.utc).isoformat():
            (350 if 28 <= index < 69 else 0)
            for index in range(96)
        }
        hass.states.states[f"sensor.{direction}_energy_production_today"] = fx.state(
            30, fx.NOW, unit="kWh", wh_period_15m=buckets)
    with patch.dict(sys.modules, stubs):
        draining = planner.calculate_plan(hass, payload)
        assert draining["calibration"]["heute_e"]["ok"] is False
        assert draining["calibration"]["heute_e"]["longest_h"] == 10.25
        assert draining["calibration"]["heute_e"]["required_h"] == 10.3
        assert draining["calibration"]["phase"] == "drain"
        assert draining["calibration"]["vormerkungen"] == []
        hass.states.states["sensor.marstek_venus_e_soc"] = fx.state(13, fx.NOW, "%")
        for expected in ("empty_rest", "wait", "charge"):
            hass.states.states["input_text.speicher_ladelogik_ae_kalibrierung_sitzung"] = fx.state(
                draining["session"], fx.NOW)
            draining = planner.calculate_plan(hass, payload)
            assert draining["calibration"]["phase"] == expected
    assert draining["calibration"]["leistung_w"] == 500


def test_pause_reason_survives_resume_through_the_real_calibration_sensor():
    hass, payload = _waiting_venus_e()
    hass.states.states["sensor.marstek_venus_e_min_zelltemperatur"] = fx.state(
        "unavailable", fx.NOW, "°C")
    with patch.dict(sys.modules, stubs):
        paused = planner.calculate_plan(hass, payload)
        assert paused["calibration"]["phase"] == "paused"
        assert "Pausiert" in paused["calibration"]["letzte_pause_grund"]
        hass.states.states["input_text.speicher_ladelogik_ae_kalibrierung_sitzung"] = fx.state(
            paused["session"], fx.NOW)
        hass.states.states["sensor.speicher_ladelogik_ae_kalibrierung"] = fx.state(
            "Pausiert", fx.NOW,
            letzte_pause_grund=paused["calibration"]["letzte_pause_grund"],
            letzte_pause_ts=paused["calibration"]["letzte_pause_ts"])
        hass.states.states["sensor.marstek_venus_e_min_zelltemperatur"] = fx.state(24, fx.NOW, "°C")
        resumed = planner.calculate_plan(hass, payload)
    assert resumed["calibration"]["phase"] == "wait"
    assert resumed["calibration"]["grund_code"] == "resumed"
    assert resumed["calibration"]["letzte_pause_grund"] == paused["calibration"]["letzte_pause_grund"]


def test_short_verified_pause_preserves_elapsed_lower_rest_but_long_gap_restarts_it():
    hass, payload = _waiting_venus_e(phase="empty_rest", pause_minutes=45)
    resting = fx.persistence.read_session(
        hass.states.get("input_text.speicher_ladelogik_ae_kalibrierung_sitzung").state)
    resting["t"] = fx.NOW - 40 * 60
    hass.states.states["input_text.speicher_ladelogik_ae_kalibrierung_sitzung"] = fx.state(
        fx.persistence.encode_session(resting), fx.NOW)
    hass.states.states["sensor.marstek_venus_e_min_zelltemperatur"] = fx.state(
        "unavailable", fx.NOW, "°C")
    with patch.dict(sys.modules, stubs):
        paused = planner.calculate_plan(hass, payload)
        assert paused["calibration"]["phase"] == "paused"
        assert fx.persistence.read_session(paused["session"])["l"] == resting["t"]
        for gap, expected in ((60, 4 * 60), (120, 45 * 60)):
            payload["now"] = fx.NOW + gap
            hass.states.states["input_text.speicher_ladelogik_ae_kalibrierung_sitzung"] = fx.state(
                paused["session"], fx.NOW + gap)
            hass.states.states["sensor.marstek_venus_e_min_zelltemperatur"] = fx.state(
                24, fx.NOW + gap, "°C")
            hass.states.states["sensor.marstek_venus_e_ac_leistung"] = fx.state(
                0, fx.NOW + gap, "W")
            resumed = planner.calculate_plan(hass, payload)
            assert resumed["calibration"]["phase"] == "empty_rest"
            assert resumed["calibration"]["ruhe_verbleibend_s"] == expected


def test_lower_rest_is_preferred_but_live_pv_can_start_charge_early_and_record_duration():
    hass, payload = _waiting_venus_e(phase="empty_rest", pause_minutes=45)
    session = fx.persistence.read_session(
        hass.states.get("input_text.speicher_ladelogik_ae_kalibrierung_sitzung").state)
    session["t"] = fx.NOW - 10 * 60
    hass.states.states["input_text.speicher_ladelogik_ae_kalibrierung_sitzung"] = fx.state(
        fx.persistence.encode_session(session), fx.NOW)
    with patch.dict(sys.modules, stubs):
        ready = planner.calculate_plan(hass, payload)
        assert ready["calibration"]["phase"] == "wait"
        assert ready["calibration"]["heute_e"]["ok"] is True
        hass.states.states["input_text.speicher_ladelogik_ae_kalibrierung_sitzung"] = fx.state(
            ready["session"], fx.NOW)
        charging = planner.calculate_plan(hass, payload)
        assert charging["calibration"]["phase"] == "charge"
        assert charging["calibration"]["letzte_ruhe_vor_laden_s_e"] == 10 * 60
        assert charging["learning"]["last_precharge_rest"]["E"]["seconds"] == 10 * 60
        hass.states.states["sensor.speicher_ladelogik_ae_lernspeicher"] = fx.state(
            "bereit", fx.NOW, **charging["learning"])
        hass.states.states["input_text.speicher_ladelogik_ae_kalibrierung_sitzung"] = fx.state(
            charging["session"], fx.NOW)
        continued = planner.calculate_plan(hass, payload)
    assert continued["calibration"]["letzte_ruhe_vor_laden_s_e"] == 10 * 60


def test_lower_rest_waits_when_live_pv_is_insufficient():
    hass, payload = _waiting_venus_e(phase="empty_rest", pause_minutes=45)
    session = fx.persistence.read_session(
        hass.states.get("input_text.speicher_ladelogik_ae_kalibrierung_sitzung").state)
    session["t"] = fx.NOW - 10 * 60
    hass.states.states["input_text.speicher_ladelogik_ae_kalibrierung_sitzung"] = fx.state(
        fx.persistence.encode_session(session), fx.NOW)
    hass.states.states["sensor.aktuelle_pv_leistung"] = fx.state(150, fx.NOW, "W")
    with patch.dict(sys.modules, stubs):
        result = planner.calculate_plan(hass, payload)
    assert result["calibration"]["phase"] == "empty_rest"
    assert result["calibration"]["ruhe_verbleibend_s"] == 35 * 60


def test_remaining_precharge_rest_does_not_invalidate_a_sufficient_short_window():
    hass, payload = _waiting_venus_e(phase="empty_rest", pause_minutes=45)
    session = fx.persistence.read_session(
        hass.states.get("input_text.speicher_ladelogik_ae_kalibrierung_sitzung").state)
    session["t"] = fx.NOW - 10 * 60
    hass.states.states["input_text.speicher_ladelogik_ae_kalibrierung_sitzung"] = fx.state(
        fx.persistence.encode_session(session), fx.NOW)
    for direction in ("sw", "so", "no"):
        buckets = {
            datetime.fromtimestamp(fx.DAY + index * 900, timezone.utc).isoformat():
            (350 if 28 <= index < 66 else 0)
            for index in range(96)
        }
        hass.states.states[f"sensor.{direction}_energy_production_today"] = fx.state(
            30, fx.NOW, unit="kWh", wh_period_15m=buckets)
    with patch.dict(sys.modules, stubs):
        result = planner.calculate_plan(hass, payload)
    assert result["calibration"]["heute_e"]["ok"] is True
    assert result["calibration"]["heute_e"]["longest_h"] == 9.5
    assert result["calibration"]["phase"] == "wait"


def test_temporary_low_live_pv_does_not_discard_later_calibration_window():
    hass, payload = _waiting_venus_e(phase="wait")
    hass.states.states["sensor.aktuelle_pv_leistung"] = fx.state(1050, fx.NOW, "W")
    for direction in ("sw", "so", "no"):
        buckets = {
            datetime.fromtimestamp(fx.DAY + index * 900, timezone.utc).isoformat():
            (175 if 28 <= index < 76 else 0)
            for index in range(96)
        }
        hass.states.states[f"sensor.{direction}_energy_production_today"] = fx.state(
            30, fx.NOW, unit="kWh", wh_period_15m=buckets)
    with patch.dict(sys.modules, stubs):
        result = planner.calculate_plan(hass, payload)
    assert result["plan"]["prognose_kurzfristfaktor"] == 0.5
    assert result["calibration"]["heute_e"]["ok"] is True
    assert result["calibration"]["heute_e"]["longest_h"] == 10.5
