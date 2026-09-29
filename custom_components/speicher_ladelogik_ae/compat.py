"""Native entity resolution for the independent A/E integration."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def legacy_entity_id(entity_id: str) -> None:
    """The new integration deliberately has no predecessor entity aliases."""
    return None


def get_state_with_legacy_fallback(states: Any, entity_id: str):
    """Read only this integration's own state or the selected physical entity."""
    return states.get(entity_id)


def first_existing_state(states: Any, entity_ids: Iterable[str]):
    for entity_id in entity_ids:
        state = states.get(entity_id)
        if state is not None:
            return state, entity_id
    return None, None


def compatibility_entity_ids(entity_ids: Iterable[str]) -> list[str]:
    return []
