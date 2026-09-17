"""Speicher-Ladelogik integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event

from .const import CONF_ENABLED_MODELS, PLATFORMS
from .coordinator import SpeicherLadelogikCoordinator
from .panel import async_register_panel, async_unregister_panel


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Speicher-Ladelogik from a config entry."""
    coordinator = SpeicherLadelogikCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    entry.async_on_unload(
        async_track_state_change_event(
            hass,
            coordinator.tracked_entities,
            coordinator.async_handle_state_change,
        )
    )
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_register_panel(hass, entry)
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate the original A/E entry to the selectable model layout."""
    if entry.version < 2:
        data = dict(entry.data)
        data.setdefault(CONF_ENABLED_MODELS, ["A", "E"])
        hass.config_entries.async_update_entry(entry, data=data, version=2)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Speicher-Ladelogik config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        async_unregister_panel(hass)
    return unloaded


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload after an entry update."""
    await hass.config_entries.async_reload(entry.entry_id)
