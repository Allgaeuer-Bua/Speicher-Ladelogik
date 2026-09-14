"""Data coordinator for Speicher-Ladelogik."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    COMMON_KEYS,
    CONF_A_AC_POWER,
    CONF_A_SOC,
    CONF_E_AC_POWER,
    CONF_E_SOC,
    CONF_MPPT_SENSORS,
    CONF_PV_AC,
    DOMAIN,
    REQUIRED_A_KEYS,
    REQUIRED_COMMON_KEYS,
    REQUIRED_E_KEYS,
    UPDATE_INTERVAL_SECONDS,
    VENUS_A_KEYS,
    VENUS_E_KEYS,
    VERSION,
)
from .helpers import as_number, is_usable_state, power_in_watts

_LOGGER = logging.getLogger(__name__)


class SpeicherLadelogikCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Collect configured Home Assistant entity states without writing anything."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
            always_update=False,
        )
        self.entry = entry
        self.config = dict(entry.data)

    @property
    def tracked_entities(self) -> list[str]:
        """Return every configured entity ID once."""
        entities: list[str] = []
        for value in self.config.values():
            candidates = value if isinstance(value, list) else [value]
            for candidate in candidates:
                if isinstance(candidate, str) and "." in candidate:
                    entities.append(candidate)
        return list(dict.fromkeys(entities))

    async def _async_update_data(self) -> dict[str, Any]:
        return self._collect_data()

    @callback
    def async_handle_state_change(self, _event: Event) -> None:
        """Refresh immediately when a configured entity changes."""
        self.async_set_updated_data(self._collect_data())

    def _snapshot(self, entity_id: str) -> dict[str, Any]:
        state = self.hass.states.get(entity_id)
        if state is None:
            return {
                "entity_id": entity_id,
                "available": False,
                "state": None,
                "unit": None,
                "age_min": None,
            }

        reported = getattr(state, "last_reported", state.last_updated)
        age_min = max(0.0, (dt_util.utcnow() - reported).total_seconds() / 60)
        return {
            "entity_id": entity_id,
            "available": is_usable_state(state.state),
            "state": state.state,
            "unit": state.attributes.get("unit_of_measurement"),
            "age_min": round(age_min, 1),
        }

    def _snapshots_for_key(self, key: str) -> list[dict[str, Any]]:
        value = self.config.get(key)
        entities = value if isinstance(value, list) else [value]
        return [self._snapshot(entity) for entity in entities if isinstance(entity, str)]

    def _key_available(self, key: str) -> bool:
        snapshots = self._snapshots_for_key(key)
        return bool(snapshots) and all(item["available"] for item in snapshots)

    def _numeric(self, key: str, *, power: bool = False) -> float | None:
        snapshots = self._snapshots_for_key(key)
        if not snapshots or not snapshots[0]["available"]:
            return None
        if power:
            return power_in_watts(snapshots[0]["state"], snapshots[0]["unit"])
        return as_number(snapshots[0]["state"])

    def _collect_data(self) -> dict[str, Any]:
        sources: dict[str, list[dict[str, Any]]] = {}
        for key in (*COMMON_KEYS, *VENUS_A_KEYS, *VENUS_E_KEYS):
            sources[key] = self._snapshots_for_key(key)

        pv_ac_w = self._numeric(CONF_PV_AC, power=True)
        mppt_values = [
            power_in_watts(item["state"], item["unit"])
            for item in sources[CONF_MPPT_SENSORS]
            if item["available"]
        ]
        mppt_complete = bool(sources[CONF_MPPT_SENSORS]) and len(mppt_values) == len(
            sources[CONF_MPPT_SENSORS]
        )
        mppt_sum_w = sum(value for value in mppt_values if value is not None) if (
            mppt_complete and all(value is not None for value in mppt_values)
        ) else None

        if pv_ac_w is not None and (pv_ac_w > 0 or not mppt_sum_w):
            pv_plan_w = max(0.0, pv_ac_w)
            pv_source = "AC-Messung"
        elif mppt_sum_w is not None:
            pv_plan_w = max(0.0, mppt_sum_w * 0.95)
            pv_source = "MPPT-Fallback (95 %)"
        else:
            pv_plan_w = None
            pv_source = "nicht verfügbar"

        missing = sorted(
            {
                item["entity_id"]
                for snapshots in sources.values()
                for item in snapshots
                if not item["available"]
            }
        )

        common_ready = all(self._key_available(key) for key in REQUIRED_COMMON_KEYS) and (
            pv_ac_w is not None or mppt_sum_w is not None
        )
        a_ready = all(self._key_available(key) for key in REQUIRED_A_KEYS)
        e_ready = all(self._key_available(key) for key in REQUIRED_E_KEYS)

        return {
            "version": VERSION,
            "betriebsart": "Beobachten",
            "schreibzugriffe_aktiv": False,
            "daten_gueltig_gemeinsam": common_ready,
            "daten_gueltig_venus_a": a_ready,
            "daten_gueltig_venus_e": e_ready,
            "daten_gueltig": common_ready and a_ready and e_ready,
            "pv_planungswert_w": round(pv_plan_w) if pv_plan_w is not None else None,
            "pv_planungswert_quelle": pv_source,
            "pv_ac_w": round(pv_ac_w) if pv_ac_w is not None else None,
            "pv_mppt_summe_dc_w": round(mppt_sum_w) if mppt_sum_w is not None else None,
            "soc_venus_a": self._numeric(CONF_A_SOC),
            "soc_venus_e": self._numeric(CONF_E_SOC),
            "ac_leistung_venus_a_w": self._numeric(CONF_A_AC_POWER, power=True),
            "ac_leistung_venus_e_w": self._numeric(CONF_E_AC_POWER, power=True),
            "fehlende_entitaeten": missing,
            "warnungen": [f"Nicht verfügbar: {entity}" for entity in missing],
            "quellen_gesamt": len(self.tracked_entities),
            "quellen_verfuegbar": len(self.tracked_entities) - len(missing),
            "quellen": sources,
        }
