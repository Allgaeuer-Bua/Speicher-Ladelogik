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
    calibration_alerts = import_module("ae_fixture.calibration_alerts")


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
    # The actual 500 W register from this fixture stays usable for the final 1 %.
    assert plan["fahrplan_ladegrenze_roh_venus_a_w"] == 500
    assert plan["soll_ladegrenze_venus_a_w"] == 500
    assert plan["fahrplan_slot_aktiv_venus_a"] is True
    assert plan["soll_ladeleistung_gesamt_w"] == 500
    assert not plan["fahrplan_slot_verriegelt"]


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
    assert result["calibration"]["phase"] == "charge"
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


def test_calibration_start_requires_600w_fresh_meter_export_and_empty_battery():
    for soc, export in ((13, 599), (15, 1500)):
        hass, payload = _waiting_venus_e(soc=soc)
        hass.states.states["sensor.stromzahler_leistung"] = fx.state(-export, fx.NOW, "W")
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
        assert first["calibration"]["phase"] == "charge"
        hass.states.states["input_text.speicher_ladelogik_ae_kalibrierung_sitzung"] = fx.state(
            first["session"], fx.NOW)
        second = planner.calculate_plan(hass, payload)
    assert second["calibration"]["phase"] == "charge"
    assert second["calibration"]["auftraege"][0]["fruehestens_ts"] == fx.DAY


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
        assert ready["calibration"]["phase"] == "charge"
        assert ready["calibration"]["heute_e"]["ok"] is True
        assert ready["calibration"]["letzte_ruhe_vor_laden_s_e"] == 10 * 60
        assert ready["learning"]["last_precharge_rest"]["E"]["seconds"] == 10 * 60
        hass.states.states["sensor.speicher_ladelogik_ae_lernspeicher"] = fx.state(
            "bereit", fx.NOW, **ready["learning"])
        hass.states.states["input_text.speicher_ladelogik_ae_kalibrierung_sitzung"] = fx.state(
            ready["session"], fx.NOW)
        charging = planner.calculate_plan(hass, payload)
        assert charging["calibration"]["phase"] == "charge"
        assert charging["calibration"]["letzte_ruhe_vor_laden_s_e"] == 10 * 60
        assert charging["learning"]["last_precharge_rest"]["E"]["seconds"] == 10 * 60


def test_lower_rest_waits_when_live_pv_is_insufficient():
    hass, payload = _waiting_venus_e(phase="empty_rest", pause_minutes=45)
    session = fx.persistence.read_session(
        hass.states.get("input_text.speicher_ladelogik_ae_kalibrierung_sitzung").state)
    session["t"] = fx.NOW - 10 * 60
    hass.states.states["input_text.speicher_ladelogik_ae_kalibrierung_sitzung"] = fx.state(
        fx.persistence.encode_session(session), fx.NOW)
    hass.states.states["sensor.aktuelle_pv_leistung"] = fx.state(150, fx.NOW, "W")
    hass.states.states["sensor.stromzahler_leistung"] = fx.state(-100, fx.NOW, "W")
    with patch.dict(sys.modules, stubs):
        result = planner.calculate_plan(hass, payload)
    assert result["calibration"]["phase"] == "wait"
    assert result["calibration"]["ruhe_verbleibend_s"] == 0


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
    assert result["calibration"]["phase"] == "charge"


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


def test_14_percent_with_uneven_packs_can_start_on_meter_export_without_full_rest():
    hass, payload = fx.scenario(primary_phase="empty_rest", secondary_phase="idle")
    hass.states.states["sensor.marstek_venus_a_soc_batterie"] = fx.state(14, fx.NOW, "%")
    hass.states.states["sensor.marstek_venus_a_soc_batteriepack_1"] = fx.state(13, fx.NOW, "%")
    hass.states.states["sensor.marstek_venus_a_soc_batteriepack_2"] = fx.state(14, fx.NOW, "%")
    controls = dict(runtime.CONTROL_DEFAULTS)
    controls.update(mode="Automatik", kalibrierung_a_freigegeben=True,
                    kalibrierung_ruhe_unten_min=60,
                    kalibrierung_sicherung="backup2|0|500|0|1500|0|2500",
                    kalibrierung_sitzung=hass.states.get(
                        "input_text.speicher_ladelogik_ae_kalibrierung_sitzung").state)
    with patch.dict(sys.modules, stubs):
        hass.states.states.update(runtime.planner_states(controls))
        result = planner.calculate_plan(hass, payload)
    assert result["calibration"]["phase"] == "charge"
    assert result["calibration"]["letzte_ruhe_vor_laden_s_a"] == 100
    assert result["calibration"]["ruhedauer_unten_min"] == 60


def test_short_forecast_does_not_abort_prepared_battery_or_running_charge():
    hass, payload = _waiting_venus_e(phase="drain", soc=20)
    for direction in ("sw", "so", "no"):
        key = f"sensor.{direction}_energy_production_today"
        hass.states.states[key] = fx.state(0, fx.NOW, unit="kWh", wh_period_15m={})
    with patch.dict(sys.modules, stubs):
        draining = planner.calculate_plan(hass, payload)
    assert draining["calibration"]["heute_e"]["ok"] is False
    assert draining["calibration"]["phase"] == "drain"

    hass, payload = fx.scenario(primary_phase="charge", secondary_phase="idle")
    hass.states.states["sensor.stromzahler_leistung"] = fx.state(-100, fx.NOW, "W")
    for direction in ("sw", "so", "no"):
        hass.states.states[f"sensor.{direction}_energy_production_today"] = fx.state(
            0, fx.NOW, unit="kWh", wh_period_15m={})
    with patch.dict(sys.modules, stubs):
        charging = planner.calculate_plan(hass, payload)
    assert charging["calibration"]["phase"] == "charge"


def test_calibration_push_conditions_are_advisory_and_specific():
    calibration = {
        "laufende_laeufe": [{"batterie": "E", "name": "Venus E", "phase": "charge",
                            "start_ts": fx.NOW - 600, "unter_400_seit_ts": fx.NOW - 301}],
        "netzleistung_w": -100, "ruhedauer_unten_min": 45,
        "letzte_ruhe_vor_laden_s_e": 300,
        "letzte_ruhe_vor_laden_ts_e": fx.NOW - 600,
        "leistung_w": 500, "heute_e": {"ok": False, "longest_h": 8, "energy_kwh": 5.15},
    }
    alerts = calibration_alerts.active_alerts(calibration, {"E": -350}, fx.NOW)
    assert {key[2] for key in alerts} == {"short_rest", "short_window", "low_export", "low_charge"}
    assert all("läuft weiter" in message for message in alerts.values())
    calibration["laufende_laeufe"][0]["unter_400_seit_ts"] = fx.NOW - 60
    assert not any(key[2] == "low_charge" for key in calibration_alerts.active_alerts(calibration, {"E": 0}, fx.NOW))


def test_running_calibration_continues_below_400w_and_past_forecast_end():
    hass, payload = fx.scenario(primary_phase="charge", secondary_phase="idle")
    session_key = "input_text.speicher_ladelogik_ae_kalibrierung_sitzung"
    session = fx.persistence.read_session(hass.states.get(session_key).state)
    session.update(t=fx.NOW - 1800, x=fx.NOW - 3600, l=fx.NOW - 400,
                   q=fx.NOW - 15, h=1)
    hass.states.states[session_key] = fx.state(fx.persistence.encode_session(session), fx.NOW)
    hass.states.states["sensor.marstek_venus_a_ac_leistung"] = fx.state(-350, fx.NOW, "W")
    hass.states.states["sensor.stromzahler_leistung"] = fx.state(-100, fx.NOW, "W")
    with patch.dict(sys.modules, stubs):
        result = planner.calculate_plan(hass, payload)
    assert result["calibration"]["phase"] == "charge"
    assert result["calibration"]["laufende_laeufe"][0]["unter_400_seit_ts"] == fx.NOW - 400


def _normal_plan(*, pv=5000, soc_a=40, soc_e=50, controls=None):
    hass, payload = fx.scenario(primary_phase="idle", secondary_phase="idle", pv=pv, live_load=500)
    for key in ("sensor.marstek_venus_a_soc_batterie", "sensor.marstek_venus_a_soc_batteriepack_1", "sensor.marstek_venus_a_soc_batteriepack_2"):
        hass.states.states[key] = fx.state(soc_a, fx.NOW, "%")
    hass.states.states["sensor.marstek_venus_e_soc"] = fx.state(soc_e, fx.NOW, "%")
    hass.states.states["sensor.stromzahler_leistung"] = fx.state(-(pv - 500), fx.NOW, "W")
    values = dict(runtime.CONTROL_DEFAULTS)
    values.update(mode="Automatik", fruehes_ladeziel_a_stark_soc=60,
                  fruehes_ladeziel_e_stark_soc=60)
    values.update(controls or {})
    with patch.dict(sys.modules, stubs):
        hass.states.states.update(runtime.planner_states(values))
    return hass, payload


def test_normal_planner_releases_both_at_preferred_power_with_no_locked_pause():
    hass, payload = _normal_plan()
    payload["prior_plan"] = {"berechnet_ts": fx.NOW - 20, "betriebsart": "Automatik",
                             "regelung_aktiv": True, "daten_gueltig": True,
                             "fahrplan_slot_start_ts": int(fx.NOW // 900) * 900,
                             "fahrplan_slot_aktiv_venus_a": False,
                             "fahrplan_ladegrenze_stabil_venus_a_w": 0}
    with patch.dict(sys.modules, stubs):
        result = planner.calculate_plan(hass, payload)
    plan = result["plan"]
    assert plan["soll_ladegrenze_venus_a_w"] == 1100
    assert plan["soll_ladegrenze_venus_e_w"] == 1300
    assert not plan["fahrplan_slot_verriegelt"]
    assert plan["ladefreigabe_venus_a_seit_ts"] == fx.NOW
    assert any(c["battery"] == "A" and c["value"] == 1100 for c in result["proposed_commands"])


def test_manual_e_does_not_change_automatic_a_decision_or_diagnostic_reason():
    hass, payload = _normal_plan(controls={"manuell_e_aktiv": True, "manuell_laden_e_w": 500})
    with patch.dict(sys.modules, stubs):
        plan = planner.calculate_plan(hass, payload)["plan"]
    assert plan["soll_ladegrenze_venus_e_w"] == 500
    assert plan["soll_ladegrenze_venus_a_w"] == 1100
    assert not plan["fahrplan_slot_aktiv_venus_e"]
    assert "Manuelle Grenze nur für E" not in plan["leistungsentscheidung_venus_a"]["grund"]


def test_own_bad_pack_data_stops_a_but_e_can_still_charge():
    hass, payload = _normal_plan()
    hass.states.states["sensor.marstek_venus_a_soc_batteriepack_2"] = fx.state("unavailable", fx.NOW)
    with patch.dict(sys.modules, stubs):
        plan = planner.calculate_plan(hass, payload)["plan"]
    assert plan["soll_ladegrenze_venus_a_w"] == 0
    assert plan["soll_ladegrenze_venus_e_w"] == 1300


def test_shared_bad_live_data_stops_both_and_recovery_keeps_daily_release():
    hass, payload = _normal_plan()
    with patch.dict(sys.modules, stubs):
        first = planner.calculate_plan(hass, payload)["plan"]
        payload["prior_plan"] = first
        hass.states.states["sensor.stromzahler_leistung"] = fx.state("unavailable", fx.NOW)
        stopped = planner.calculate_plan(hass, payload)["plan"]
        assert stopped["soll_ladegrenze_venus_a_w"] == stopped["soll_ladegrenze_venus_e_w"] == 0
        payload["prior_plan"] = stopped
        hass.states.states["sensor.stromzahler_leistung"] = fx.state(-4500, fx.NOW, "W")
        recovered = planner.calculate_plan(hass, payload)["plan"]
    assert recovered["soll_ladegrenze_venus_a_w"] == 1100
    assert recovered["soll_ladegrenze_venus_e_w"] == 1300


def test_weak_day_ignores_configured_peak_switch_in_actual_planner():
    hass, payload = _normal_plan(controls={"schwacher_tag": 150, "mittlerer_tag": 160, "starker_tag": 180})
    with patch.dict(sys.modules, stubs):
        plan = planner.calculate_plan(hass, payload)["plan"]
    assert plan["tagesklasse"] == "schwach"
    assert plan["mittagsspitzen_konfiguriert"]
    assert not plan["mittagsspitzen_aktiv"]
    assert not plan["mittagsspitzen_planbar"]
    assert plan["soll_ladegrenze_venus_a_w"] == 1100
    assert plan["soll_ladegrenze_venus_e_w"] == 1300


def test_forecast_safety_applies_once_to_the_shared_remaining_pv():
    values = []
    for percent in (100, 80):
        hass, payload = _normal_plan(controls={"prognose_sicherheit": percent, "unplanbare_reserve": 0})
        with patch.dict(sys.modules, stubs):
            plan = planner.calculate_plan(hass, payload)["plan"]
        values.append(plan["sicher_speicherbar_rest_kwh"])
    # The forecast is lowered before subtracting house demand, never per battery.
    assert values[1] < values[0] * 0.8
    assert values[1] > values[0] * 0.6


def test_classification_has_three_yield_classes_and_confirms_changes():
    assert stability.stable_day_class(20, (25, 50, 85), fx.NOW, fx.DAY, {})[0] == "schwach"
    for expected in (30, 70):
        assert stability.stable_day_class(expected, (25, 50, 85), fx.NOW, fx.DAY, {})[0] == "mittel"
    prior = {"berechnet_ts": fx.NOW - 30, "tagesklasse": "mittel"}
    category, candidate, since = stability.stable_day_class(90, (25, 50, 85), fx.NOW, fx.DAY, prior)
    assert (category, candidate, since) == ("mittel", "stark", fx.NOW)
    prior.update(tagesklasse_kandidat=candidate, tagesklasse_kandidat_seit_ts=since)
    assert stability.stable_day_class(90, (25, 50, 85), fx.NOW + 900, fx.DAY, prior)[0] == "stark"
