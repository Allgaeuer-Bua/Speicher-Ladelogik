"""Serve the Lovelace card; expose configuration and guarded manual changes."""

from __future__ import annotations

from pathlib import Path

import voluptuous as vol
from homeassistant.components import frontend, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.service import async_register_admin_service

from .const import DOMAIN, VERSION
from .panel import PANEL_STATIC_PATH, PANEL_URL_PATH, panel_entity_config, panel_source_config
from .storage import normalize_config


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/config"})
@callback
def websocket_config(hass, connection, msg):
    """Return entity mappings only, never credentials or notify configuration."""
    registry = er.async_get(hass)
    configurations = []
    for entry in hass.data.get(DOMAIN, {}).get("lovelace_entries", {}).values():
        normalized, _ = normalize_config(dict(entry.data))
        configurations.append({
            "entry_id": entry.entry_id,
            "version": VERSION,
            "models": ["A", "E"],
            "entities": panel_entity_config(entry, registry),
            "sources": panel_source_config(entry),
            "storage_labels": normalized.get("slot_names", {}),
            "storage_models": normalized.get("slot_models", {}),
        })
    connection.send_result(msg["id"], {"entries": configurations})


@callback
def async_register_api(hass: HomeAssistant) -> None:
    """Register API once; manual writes require an administrator."""
    websocket_api.async_register_command(hass, websocket_config)

    async def apply_manual(call):
        entries = hass.data.get(DOMAIN, {}).get("lovelace_entries", {})
        entry = entries.get(call.data["entry_id"])
        if entry is None:
            raise HomeAssistantError("Speicher-Ladelogik ist nicht geladen")
        await entry.runtime_data.async_apply_manual(
            call.data["battery"], active=call.data["active"],
            charge=call.data.get("charge_w"), discharge=call.data.get("discharge_w"),
        )

    async_register_admin_service(hass, DOMAIN, "apply_manual", apply_manual, schema=vol.Schema({
        vol.Required("entry_id"): str,
        vol.Required("battery"): vol.In(["A", "E"]),
        vol.Required("active"): bool,
        vol.Optional("charge_w"): vol.Coerce(float),
        vol.Optional("discharge_w"): vol.Coerce(float),
    }))


async def async_register_frontend(hass: HomeAssistant, entry) -> None:
    """Serve local modules without creating a sidebar panel or changing Lovelace."""
    data = hass.data.setdefault(DOMAIN, {})
    if not data.get("lovelace_static_registered"):
        await hass.http.async_register_static_paths([
            StaticPathConfig(PANEL_STATIC_PATH, str(Path(__file__).parent / "frontend"), cache_headers=False)
        ])
        data["lovelace_static_registered"] = True
    data.setdefault("lovelace_entries", {})[entry.entry_id] = entry
    # The old custom panel is not recreated. Existing user-owned dashboards stay untouched.
    frontend.async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)


@callback
def async_unregister_frontend(hass: HomeAssistant, entry) -> None:
    """Stop exposing an unloaded config entry; retain the shared static resource."""
    hass.data.get(DOMAIN, {}).get("lovelace_entries", {}).pop(entry.entry_id, None)
