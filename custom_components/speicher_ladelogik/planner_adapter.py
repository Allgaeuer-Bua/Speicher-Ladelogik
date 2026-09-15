"""Adapter between configured Home Assistant entities and the shadow planner."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .compat import first_existing_state, get_state_with_legacy_fallback
from .const import (
    CONF_A_CHARGE_OVERRIDE,
    CONF_E_CHARGE_OVERRIDE,
    DEFAULTS,
)
from .planner import calculate_shadow_plan
from .runtime import PlannerState, planner_states

LEGACY_OVERRIDE_ENTITIES = {
    CONF_A_CHARGE_OVERRIDE: "input_boolean.venus_a_nicht_laden",
    CONF_E_CHARGE_OVERRIDE: "input_boolean.venus_e_nicht_laden",
}

COMPARISON_FIELDS = {
    "status": None,
    "daten_gueltig": None,
    "daten_gueltig_gemeinsam": None,
    "daten_gueltig_venus_a": None,
    "daten_gueltig_venus_e": None,
    "pv_planungswert_w": 25,
    "netto_ueberschuss_w": 25,
    "prognose_heute_erwartet_kwh": 0.05,
    "sicher_speicherbar_rest_kwh": 0.05,
    "restbedarf_venus_a_kwh": 0.02,
    "restbedarf_venus_e_kwh": 0.02,
    "soll_ladegrenze_venus_a_w": 25,
    "soll_ladegrenze_venus_e_w": 25,
    "normaler_fahrplan_status": None,
    "entscheidungsgrund": None,
}


class _MappedStates:
    """Map legacy planner entity IDs to the UI-selected entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        mapping: dict[str, str],
        overrides: dict[str, PlannerState] | None = None,
    ) -> None:
        self._hass = hass
        self._mapping = mapping
        self._overrides = overrides or {}

    def get(self, entity_id: str):
        if entity_id in self._overrides:
            return self._overrides[entity_id]
        mapped_entity_id = self._mapping.get(entity_id, entity_id)
        if mapped_entity_id != entity_id:
            return self._hass.states.get(mapped_entity_id)
        return get_state_with_legacy_fallback(self._hass.states, entity_id)


class _MappedHomeAssistant:
    """Minimal Home Assistant facade required by the pure planner."""

    def __init__(
        self,
        hass: HomeAssistant,
        mapping: dict[str, str],
        overrides: dict[str, PlannerState] | None = None,
    ) -> None:
        self.states = _MappedStates(hass, mapping, overrides)


def _entity_mapping(config: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for key, legacy in DEFAULTS.items():
        configured = config.get(key, legacy)
        if isinstance(legacy, list):
            if isinstance(configured, list):
                mapping.update(
                    {
                        old: new
                        for old, new in zip(legacy, configured, strict=False)
                        if isinstance(new, str)
                    }
                )
        elif isinstance(legacy, str) and isinstance(configured, str):
            mapping[legacy] = configured

    for key, legacy in LEGACY_OVERRIDE_ENTITIES.items():
        configured = config.get(key)
        if isinstance(configured, str):
            mapping[legacy] = configured
    return mapping


def _local_timestamp(local_date, hour: int) -> float:
    zone = dt_util.DEFAULT_TIME_ZONE
    return datetime.combine(local_date, time(hour=hour), tzinfo=zone).timestamp()


def calculate(
    hass: HomeAssistant,
    config: dict[str, Any],
    prior_plan: dict[str, Any] | None = None,
    request: str = "tick",
    control: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run one planner calculation."""
    now = dt_util.now()
    today = now.date()
    mapping = _entity_mapping(config)
    proxy = _MappedHomeAssistant(
        hass,
        mapping,
        planner_states(control) if control is not None else None,
    )
    result = calculate_shadow_plan(
        proxy,
        {
            "request": request,
            "now": now.timestamp(),
            "day0": _local_timestamp(today, 0),
            "day1": _local_timestamp(today + timedelta(days=1), 0),
            "day2": _local_timestamp(today + timedelta(days=2), 0),
            "nine": _local_timestamp(today, 9),
            "eleven": _local_timestamp(today, 11),
            "deadline": _local_timestamp(today, 15),
            "prepare": _local_timestamp(today, 18),
            "prior_plan": prior_plan,
        },
    )
    for command_key in ("commands", "proposed_commands"):
        for command in result.get(command_key, []):
            command["entity"] = mapping.get(command["entity"], command["entity"])
    if control is not None:
        mode = str(control.get("mode", "Beobachten"))
        plan = result.get("plan", {})
        plan["betriebsart"] = mode
        plan["regelung_aktiv"] = mode == "Automatik" and bool(
            plan.get("regelung_aktiv")
        )
    return result


def _equal(left: Any, right: Any, tolerance: float | None) -> bool:
    if tolerance is None:
        return left == right
    try:
        return abs(float(left) - float(right)) <= tolerance
    except (TypeError, ValueError):
        return left == right


def compare_with_legacy(
    hass: HomeAssistant,
    shadow_plan: dict[str, Any],
    shadow_calibration: dict[str, Any],
) -> dict[str, Any]:
    """Compare selected shadow values with the still-running legacy sensors."""
    legacy_plan, legacy_plan_entity_id = first_existing_state(
        hass.states,
        ("sensor.pv_ladelogik_planung",),
    )
    legacy_calibration, legacy_calibration_entity_id = first_existing_state(
        hass.states,
        ("sensor.pv_kalibrierung_planung",),
    )
    if legacy_plan is None:
        return {
            "available": False,
            "matches": None,
            "fields_compared": 0,
            "differences": [],
            "referenz_plan_entitaet": None,
            "referenz_kalibrierung_entitaet": legacy_calibration_entity_id,
        }

    differences: list[dict[str, Any]] = []
    compared = 0
    for field, tolerance in COMPARISON_FIELDS.items():
        old_value = (
            legacy_plan.state
            if field == "status"
            else legacy_plan.attributes.get(field)
        )
        new_value = shadow_plan.get(field)
        compared += 1
        if not _equal(old_value, new_value, tolerance):
            differences.append({"feld": field, "alt": old_value, "schatten": new_value})

    if legacy_calibration is not None:
        compared += 1
        old_phase = legacy_calibration.attributes.get("phase_intern")
        new_phase = shadow_calibration.get("phase")
        if old_phase != new_phase:
            differences.append(
                {"feld": "kalibrierphase", "alt": old_phase, "schatten": new_phase}
            )

    held = {
        key: bool(shadow_plan.get("sollwert_venus_" + key + "_gehalten"))
        for key in ("a", "e")
    }
    latched = {
        key: bool(shadow_plan.get("ziel_venus_" + key + "_latch_aktiv"))
        for key in ("a", "e")
    }
    stability_active = any((*held.values(), *latched.values()))
    aggregate_fields = {
        "status",
        "sicher_speicherbar_rest_kwh",
        "normaler_fahrplan_status",
        "entscheidungsgrund",
    }
    for difference in differences:
        field = difference["feld"]
        difference["beabsichtigt"] = bool(
            (stability_active and field in aggregate_fields)
            or (field == "restbedarf_venus_a_kwh" and latched["a"])
            or (field == "restbedarf_venus_e_kwh" and latched["e"])
            or (field == "soll_ladegrenze_venus_a_w" and held["a"])
            or (field == "soll_ladegrenze_venus_e_w" and held["e"])
        )
    unintentional = [
        difference for difference in differences if not difference["beabsichtigt"]
    ]

    return {
        "available": True,
        "matches": not differences,
        "funktional_passend": not unintentional,
        "fields_compared": compared,
        "differences": differences,
        "beabsichtigte_abweichungen": len(differences) - len(unintentional),
        "sonstige_abweichungen": len(unintentional),
        "referenz_plan_entitaet": legacy_plan_entity_id,
        "referenz_kalibrierung_entitaet": legacy_calibration_entity_id,
    }
