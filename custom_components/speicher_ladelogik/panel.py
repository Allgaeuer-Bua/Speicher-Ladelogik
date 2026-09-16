"""Automatic Home Assistant sidebar panel for Speicher-Ladelogik."""

from __future__ import annotations

import logging
from hashlib import sha256
from pathlib import Path
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import (
    CONF_A_AC_POWER,
    CONF_A_MAX_CELL_TEMP,
    CONF_A_MAX_CELL_VOLTAGE,
    CONF_A_MAX_SOC,
    CONF_A_MIN_CELL_TEMP,
    CONF_A_MIN_SOC,
    CONF_A_PACK_DRIFT,
    CONF_A_PACK_SOC,
    CONF_A_SOC,
    CONF_E_AC_POWER,
    CONF_E_CELL_DRIFT,
    CONF_E_MAX_CELL_TEMP,
    CONF_E_MAX_CELL_VOLTAGE,
    CONF_E_MAX_SOC,
    CONF_E_MIN_CELL_TEMP,
    CONF_E_MIN_SOC,
    CONF_E_SOC,
    CONF_GRID_POWER,
    CONF_HOUSE_POWER,
    CONF_PV_AC,
    DOMAIN,
    NAME,
    VERSION,
)

_LOGGER = logging.getLogger(__name__)

PANEL_URL_PATH: Final = "speicher-ladelogik"
PANEL_STATIC_PATH: Final = "/speicher_ladelogik_static"
PANEL_TITLE: Final = "Speicher-Ladelogik"
PANEL_ICON: Final = "mdi:battery-charging-medium"
PANEL_ELEMENT: Final = f"speicher-ladelogik-panel-{VERSION.replace('.', '-')}"

_STATIC_REGISTERED = "panel_static_registered"
_PANEL_REGISTERED = "panel_registered"

# Native entities are resolved through their stable unique IDs. The dashboard
# therefore keeps working after a user changes an entity ID in Home Assistant.
PANEL_ENTITIES: Final = {
    "status": ("sensor", "status"),
    "pv_planungswert": ("sensor", "pv_planungswert"),
    "daten_gemeinsam": ("sensor", "daten_gemeinsam"),
    "daten_venus_a": ("sensor", "daten_venus_a"),
    "daten_venus_e": ("sensor", "daten_venus_e"),
    "planung": ("sensor", "planung"),
    "kalibrierung": ("sensor", "kalibrierung"),
    "planvergleich": ("sensor", "planvergleich"),
    "wirkungsgrad_venus_a": ("sensor", "wirkungsgrad_venus_a"),
    "verlustleistung_venus_a": ("sensor", "verlustleistung_venus_a"),
    "wirkungsgrad_venus_e": ("sensor", "wirkungsgrad_venus_e"),
    "verlustleistung_venus_e": ("sensor", "verlustleistung_venus_e"),
    "mittagsspitzen": ("switch", "mittagsspitzen"),
    "handbetrieb_venus_a": ("switch", "handbetrieb_venus_a"),
    "handbetrieb_venus_e": ("switch", "handbetrieb_venus_e"),
    "betriebsart": ("select", "betriebsart"),
    "bevorzugte_ladeleistung_venus_a": (
        "number",
        "bevorzugte_ladeleistung_venus_a",
    ),
    "bevorzugte_ladeleistung_venus_e": (
        "number",
        "bevorzugte_ladeleistung_venus_e",
    ),
    "nennkapazitaet_venus_a": ("number", "nennkapazitaet_venus_a"),
    "nennkapazitaet_venus_e": ("number", "nennkapazitaet_venus_e"),
    "manuell_laden_venus_a": ("number", "manuell_laden_venus_a"),
    "manuell_entladen_venus_a": ("number", "manuell_entladen_venus_a"),
    "manuell_laden_venus_e": ("number", "manuell_laden_venus_e"),
    "manuell_entladen_venus_e": ("number", "manuell_entladen_venus_e"),
    "mindestreserve": ("number", "mindestreserve"),
    "prognose_sicherheit": ("number", "prognose_sicherheit"),
    "unplanbare_reserve": ("number", "unplanbare_reserve"),
    "ladewirkungsgrad": ("number", "ladewirkungsgrad"),
    "planung_hysterese": ("number", "planung_hysterese"),
    "schwacher_tag": ("number", "schwacher_tag"),
    "mittlerer_tag": ("number", "mittlerer_tag"),
    "starker_tag": ("number", "starker_tag"),
    "knappheitsreserve": ("number", "knappheitsreserve"),
    "min_effiziente_leistung": ("number", "min_effiziente_leistung"),
    "venus_a_packs": ("number", "venus_a_packs"),
    "kalibrierung_venus_a_anfordern": (
        "button",
        "kalibrierung_venus_a_anfordern",
    ),
    "kalibrierung_venus_e_anfordern": (
        "button",
        "kalibrierung_venus_e_anfordern",
    ),
    "kalibrierung_venus_a_morgen": (
        "button",
        "kalibrierung_venus_a_morgen",
    ),
    "kalibrierung_venus_e_morgen": (
        "button",
        "kalibrierung_venus_e_morgen",
    ),
    "kalibrierung_venus_a_entfernen": (
        "button",
        "kalibrierung_venus_a_entfernen",
    ),
    "kalibrierung_venus_e_entfernen": (
        "button",
        "kalibrierung_venus_e_entfernen",
    ),
    "kalibrierung_abbrechen": ("button", "kalibrierung_abbrechen"),
    "fehler_quittieren": ("button", "fehler_quittieren"),
}

SOURCE_ENTITIES: Final = {
    "pv": CONF_PV_AC,
    "grid": CONF_GRID_POWER,
    "house": CONF_HOUSE_POWER,
    "soc_a": CONF_A_SOC,
    "power_a": CONF_A_AC_POWER,
    "min_soc_a": CONF_A_MIN_SOC,
    "max_soc_a": CONF_A_MAX_SOC,
    "pack_soc_a": CONF_A_PACK_SOC,
    "cell_voltage_a": CONF_A_MAX_CELL_VOLTAGE,
    "cell_temp_max_a": CONF_A_MAX_CELL_TEMP,
    "cell_temp_min_a": CONF_A_MIN_CELL_TEMP,
    "drift_a": CONF_A_PACK_DRIFT,
    "soc_e": CONF_E_SOC,
    "power_e": CONF_E_AC_POWER,
    "min_soc_e": CONF_E_MIN_SOC,
    "max_soc_e": CONF_E_MAX_SOC,
    "cell_voltage_e": CONF_E_MAX_CELL_VOLTAGE,
    "cell_temp_max_e": CONF_E_MAX_CELL_TEMP,
    "cell_temp_min_e": CONF_E_MIN_CELL_TEMP,
    "drift_e": CONF_E_CELL_DRIFT,
}


def panel_entity_config(entry: ConfigEntry, entity_registry) -> dict[str, str]:
    """Resolve the integration's native entities for the frontend panel."""
    resolved: dict[str, str] = {}
    for key, (platform, unique_key) in PANEL_ENTITIES.items():
        entity_id = entity_registry.async_get_entity_id(
            platform,
            DOMAIN,
            f"{entry.entry_id}_{unique_key}",
        )
        if entity_id:
            resolved[key] = entity_id
    return resolved


def panel_source_config(entry: ConfigEntry) -> dict[str, str | list[str]]:
    """Return configured physical source entities used by the visualisation."""
    sources: dict[str, str | list[str]] = {}
    for key, config_key in SOURCE_ENTITIES.items():
        value = entry.data.get(config_key)
        if isinstance(value, str) and value:
            sources[key] = value
        elif isinstance(value, list):
            clean = [item for item in value if isinstance(item, str) and item]
            if clean:
                sources[key] = clean
    return sources


async def async_register_panel(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Serve and register the self-contained sidebar dashboard."""
    try:
        from homeassistant.components import frontend, panel_custom
        from homeassistant.components.http import StaticPathConfig
        from homeassistant.helpers import entity_registry as er

        domain_data = hass.data.setdefault(DOMAIN, {})
        frontend_dir = Path(__file__).parent / "frontend"

        if not domain_data.get(_STATIC_REGISTERED):
            await hass.http.async_register_static_paths(
                [
                    StaticPathConfig(
                        PANEL_STATIC_PATH,
                        str(frontend_dir),
                        cache_headers=False,
                    )
                ]
            )
            domain_data[_STATIC_REGISTERED] = True

        js_file = frontend_dir / "speicher-ladelogik-panel.js"
        try:
            cache_bust = sha256(js_file.read_bytes()).hexdigest()[:12]
        except OSError:
            cache_bust = VERSION

        registry = er.async_get(hass)
        panel_config = {
            "domain": DOMAIN,
            "title": NAME,
            "version": VERSION,
            "entities": panel_entity_config(entry, registry),
            "sources": panel_source_config(entry),
        }

        try:
            frontend.async_remove_panel(
                hass,
                PANEL_URL_PATH,
                warn_if_unknown=False,
            )
        except Exception:  # noqa: BLE001 - no existing panel on first setup
            pass

        await panel_custom.async_register_panel(
            hass,
            frontend_url_path=PANEL_URL_PATH,
            webcomponent_name=PANEL_ELEMENT,
            module_url=(
                f"{PANEL_STATIC_PATH}/speicher-ladelogik-panel.js?v={cache_bust}"
            ),
            sidebar_title=PANEL_TITLE,
            sidebar_icon=PANEL_ICON,
            require_admin=False,
            config=panel_config,
        )
        domain_data[_PANEL_REGISTERED] = True
        _LOGGER.info("Registered sidebar dashboard at /%s", PANEL_URL_PATH)
    except Exception as err:  # noqa: BLE001 - dashboard must not block control
        _LOGGER.warning("Could not register sidebar dashboard: %s", err)


@callback
def async_unregister_panel(hass: HomeAssistant) -> None:
    """Remove the sidebar panel when the integration is unloaded."""
    domain_data = hass.data.get(DOMAIN, {})
    if not domain_data.get(_PANEL_REGISTERED):
        return
    try:
        from homeassistant.components import frontend

        frontend.async_remove_panel(
            hass,
            PANEL_URL_PATH,
            warn_if_unknown=False,
        )
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Could not remove sidebar dashboard: %s", err)
    finally:
        domain_data[_PANEL_REGISTERED] = False
