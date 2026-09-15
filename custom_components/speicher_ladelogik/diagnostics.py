"""Diagnostics for Speicher-Ladelogik."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .coordinator import SpeicherLadelogikCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return configuration and current read-only evaluation."""
    coordinator: SpeicherLadelogikCoordinator = entry.runtime_data
    return {
        "configuration": dict(entry.data),
        "native_controls": coordinator.control,
        "evaluation": coordinator.data,
    }
