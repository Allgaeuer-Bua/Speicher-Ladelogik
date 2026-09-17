"""Adapter between configured Home Assistant entities and the planner."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .compat import get_state_with_legacy_fallback
from .const import (
    CONF_A_CHARGE_OVERRIDE,
    CONF_A_PACK_DRIFT,
    CONF_A_PACK_SOC,
    CONF_D_CHARGE_OVERRIDE,
    CONF_D_PACK_DRIFT,
    CONF_D_PACK_SOC,
    CONF_E_CHARGE_OVERRIDE,
    CONF_E_CELL_DRIFT,
    CONF_ENABLED_MODELS,
    DEFAULTS,
)
from .planner import calculate_plan
from .runtime import PlannerState, planner_states

LEGACY_OVERRIDE_ENTITIES = {
    CONF_A_CHARGE_OVERRIDE: "input_boolean.venus_a_nicht_laden",
    CONF_D_CHARGE_OVERRIDE: "input_boolean.venus_d_nicht_laden",
    CONF_E_CHARGE_OVERRIDE: "input_boolean.venus_e_nicht_laden",
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
                        if isinstance(old, str)
                        and "." in old
                        and isinstance(new, str)
                        and "." in new
                    }
                )
        elif (
            isinstance(legacy, str)
            and "." in legacy
            and isinstance(configured, str)
            and "." in configured
        ):
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
    result = calculate_plan(
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
            "prior_plan": prior_plan,
            "battery_keys": config.get(CONF_ENABLED_MODELS, ["A", "E"]),
            "pack_entities": {
                "A": config.get(CONF_A_PACK_SOC, []),
                "D": config.get(CONF_D_PACK_SOC, []),
            },
            "drift_entities": {
                "A": config.get(CONF_A_PACK_DRIFT, []),
                "D": config.get(CONF_D_PACK_DRIFT, []),
                "E": [config.get(CONF_E_CELL_DRIFT)]
                if config.get(CONF_E_CELL_DRIFT)
                else [],
            },
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
