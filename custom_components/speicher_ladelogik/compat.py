"""Compatibility helpers for the previous YAML/Python installation."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

_EXACT_LEGACY_ENTITY_IDS = {
    "sensor.speicher_ladelogik_planung": "sensor.pv_ladelogik_planung",
    "sensor.speicher_ladelogik_kalibrierung_planung": (
        "sensor.pv_kalibrierung_planung"
    ),
    "sensor.speicher_ladelogik_lernspeicher": "sensor.pv_ladelogik_lernspeicher",
    "input_boolean.speicher_ladelogik_v1_beta_1_initialisiert": (
        "input_boolean.pv_ladelogik_rc5_initialisiert"
    ),
    "input_text.speicher_ladelogik_sicherung": ("input_text.pv_ladelogik_sicherung"),
}

_PREFIX_LEGACY_ENTITY_IDS = (
    ("input_number.speicher_ladelogik_", "input_number.pv_ladelogik_"),
    (
        "input_boolean.speicher_ladelogik_kalibrierung_",
        "input_boolean.pv_kalibrierung_",
    ),
    ("input_boolean.speicher_ladelogik_", "input_boolean.pv_ladelogik_"),
    ("input_select.speicher_ladelogik_", "input_select.pv_ladelogik_"),
    (
        "input_text.speicher_ladelogik_kalibrierung_",
        "input_text.pv_kalibrierung_",
    ),
)


def legacy_entity_id(entity_id: str) -> str | None:
    """Return the matching V2.2.1 entity ID, if the entity was renamed."""
    exact = _EXACT_LEGACY_ENTITY_IDS.get(entity_id)
    if exact is not None:
        return exact

    for current_prefix, legacy_prefix in _PREFIX_LEGACY_ENTITY_IDS:
        if entity_id.startswith(current_prefix):
            return legacy_prefix + entity_id.removeprefix(current_prefix)
    return None


def get_state_with_legacy_fallback(states: Any, entity_id: str):
    """Prefer a current entity and otherwise read its V2.2.1 predecessor."""
    state = states.get(entity_id)
    if state is not None:
        return state

    legacy = legacy_entity_id(entity_id)
    return states.get(legacy) if legacy is not None else None


def first_existing_state(states: Any, entity_ids: Iterable[str]):
    """Return the first existing state and its entity ID."""
    for entity_id in entity_ids:
        state = states.get(entity_id)
        if state is not None:
            return state, entity_id
    return None, None


def compatibility_entity_ids(entity_ids: Iterable[str]) -> list[str]:
    """Return all known legacy counterparts for an entity collection."""
    aliases = [legacy_entity_id(entity_id) for entity_id in entity_ids]
    return list(dict.fromkeys(alias for alias in aliases if alias is not None))
