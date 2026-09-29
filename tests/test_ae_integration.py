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
            "version": "2.0.0", "berechnet_ts": fx.NOW - 20,
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
