"""Data coordinator for Speicher-Ladelogik."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .compat import legacy_entity_id
from .const import (
    COMMON_KEYS,
    CONF_A_AC_POWER,
    CONF_A_ACTIVE,
    CONF_A_AUTO_TARGET,
    CONF_A_CHARGE_LIMIT,
    CONF_A_CHARGE_OVERRIDE,
    CONF_A_DISCHARGE_LIMIT,
    CONF_A_SOC,
    CONF_D_AC_POWER,
    CONF_D_ACTIVE,
    CONF_D_AUTO_TARGET,
    CONF_D_CHARGE_LIMIT,
    CONF_D_CHARGE_OVERRIDE,
    CONF_D_DISCHARGE_LIMIT,
    CONF_D_SOC,
    CONF_E_AC_POWER,
    CONF_E_ACTIVE,
    CONF_E_AUTO_TARGET,
    CONF_E_CHARGE_LIMIT,
    CONF_E_CHARGE_OVERRIDE,
    CONF_E_DISCHARGE_LIMIT,
    CONF_E_SOC,
    CONF_ENABLED_MODELS,
    CONF_MOBILE_NOTIFY_SERVICE,
    CONF_MPPT_SENSORS,
    CONF_PV_AC,
    DEFAULTS,
    DOMAIN,
    REQUIRED_COMMON_KEYS,
    UPDATE_INTERVAL_SECONDS,
    VERSION,
)
from .control import (
    BACKUP_ENTITY,
    CAL_BACKUP_ENTITY,
    LEGACY_CONTROLLER_ENTITIES,
    QUEUE_ENTITY,
    SESSION_ENTITY,
    validate_number_target,
    write_needed,
)
from .helpers import as_number, conversion_metrics, is_usable_state, power_in_watts
from .planner_adapter import calculate
from .runtime import CONTROL_DEFAULTS, HELPER_TO_CONTROL
from .storage import (
    MODEL_DEFAULT_MODULES,
    MODEL_MAXIMUM_W,
    MODEL_PREFERRED_W,
    SLOT_FIELDS,
    SLOT_KEYS,
    nominal_capacity,
    normalize_config,
)

_LOGGER = logging.getLogger(__name__)

_STABILITY_STORAGE_VERSION = 2
_STABILITY_KEYS = tuple(
    field
    for name in ("a", "d", "e")
    for field in (
        f"ziel_venus_{name}_erreicht",
        f"ziel_venus_{name}_latch_soc",
        f"fahrplan_ladegrenze_stabil_venus_{name}_w",
    )
) + (
    "betriebsart",
    "regelung_aktiv",
    "mittagsspitzen_aktiv",
    "sonnenhoechststand_ts",
    "mittagsfenster_start_ts",
    "mittagsfenster_ende_ts",
    "mindestreserve_pro_speicher_kwh",
    "mindestreserve_offen",
    "fahrplan_slot_start_ts",
    "fahrplan_slot_ende_ts",
    "fahrplan_slot_aktiv_venus_a",
    "fahrplan_slot_aktiv_venus_d",
    "fahrplan_slot_aktiv_venus_e",
)


class SpeicherLadelogikCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Collect states, calculate plans and optionally execute guarded writes."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
            always_update=False,
        )
        self.entry = entry
        # Overlay defaults so entries created by an earlier beta gain new,
        # non-required source mappings without forcing a fresh setup.
        raw_config = {**DEFAULTS, **entry.data, **entry.options}
        self.config, self.storage_instances = normalize_config(raw_config)
        self._last_plan: dict[str, Any] | None = None
        self._stored_stability: dict[str, Any] = {}
        self._control: dict[str, Any] = dict(CONTROL_DEFAULTS)
        for slot, instance in zip(SLOT_KEYS, self.storage_instances, strict=False):
            name = slot.lower()
            model = str(instance["model"])
            modules = int(instance.get("modules", MODEL_DEFAULT_MODULES.get(model, 1)))
            self._control[f"bevorzugte_ladeleistung_{name}_w"] = MODEL_PREFERRED_W[model]
            self._control[f"maximale_ladeleistung_{name}_w"] = MODEL_MAXIMUM_W[model]
            self._control[f"maximale_entladeleistung_{name}_w"] = MODEL_MAXIMUM_W[model]
            self._control[f"nennkapazitaet_{name}_kwh"] = nominal_capacity(model, modules)
            self._control[f"manuell_entladen_{name}_w"] = MODEL_MAXIMUM_W[model]
            if model in MODEL_DEFAULT_MODULES:
                self._control[f"venus_{name}_packs"] = float(modules)
        self._state_loaded = False
        self._write_lock = asyncio.Lock()
        self._pending_request = "tick"
        self._last_write_error: str | None = None
        self._last_write_ts: float | None = None
        self._last_write_results: list[dict[str, Any]] = []
        self._due_notified: tuple[str, ...] = ()
        self._problem_started_ts: float | None = None
        self._problem_signature: str | None = None
        self._mobile_problem_signature: str | None = None
        self._stability_store: Store[dict[str, Any]] = Store(
            hass,
            _STABILITY_STORAGE_VERSION,
            f"{DOMAIN}.{entry.entry_id}.state",
        )

    @property
    def enabled_models(self) -> tuple[str, ...]:
        """Return configured internal storage slots in stable order."""
        selected = self.config.get(CONF_ENABLED_MODELS, ["A", "E"])
        if not isinstance(selected, list):
            selected = ["A", "E"]
        return tuple(key for key in ("A", "D", "E") if key in selected)

    def storage_model(self, slot: str) -> str:
        """Return the physical Venus model assigned to an internal slot."""
        return str(self.config.get("slot_models", {}).get(slot, slot))

    def storage_name(self, slot: str) -> str:
        """Return the configured display name for an internal slot."""
        return str(
            self.config.get("slot_names", {}).get(
                slot, f"Venus {self.storage_model(slot)}"
            )
        )

    def storage_has_packs(self, slot: str) -> bool:
        """Return whether the physical model exposes battery packs."""
        return self.storage_model(slot) in {"A", "D"}

    @property
    def source_entities(self) -> list[str]:
        """Return every entity selected in the config flow once."""
        entities: list[str] = []
        storage_keys = {
            value for fields in SLOT_FIELDS.values() for value in fields.values()
        }
        enabled_storage_keys = {
            value
            for slot in self.enabled_models
            for value in SLOT_FIELDS[slot].values()
        }
        for key, value in self.config.items():
            if key == CONF_MOBILE_NOTIFY_SERVICE:
                continue
            if key in storage_keys and key not in enabled_storage_keys:
                continue
            if key in {"slot_models", "slot_names", "slot_ids"}:
                continue
            candidates = value if isinstance(value, list) else [value]
            for candidate in candidates:
                if isinstance(candidate, str) and "." in candidate:
                    entities.append(candidate)
        return list(dict.fromkeys(entities))

    @property
    def tracked_entities(self) -> list[str]:
        """Return physical sources plus the sun position used by the planner."""
        return list(dict.fromkeys([*self.source_entities, "sun.sun"]))

    @property
    def write_enabled(self) -> bool:
        """Return whether this runtime is allowed to write device registers."""
        return self._control.get("mode") == "Automatik"

    @property
    def control(self) -> dict[str, Any]:
        """Return a copy of persistent native integration controls."""
        return dict(self._control)

    def _sync_model_controls(self) -> None:
        """Keep module-derived capacities and model power bounds consistent."""
        for slot in self.enabled_models:
            name = slot.lower()
            model = self.storage_model(slot)
            maximum = MODEL_MAXIMUM_W[model]
            for field in (
                f"bevorzugte_ladeleistung_{name}_w",
                f"maximale_ladeleistung_{name}_w",
                f"maximale_entladeleistung_{name}_w",
                f"manuell_laden_{name}_w",
                f"manuell_entladen_{name}_w",
            ):
                self._control[field] = max(
                    0.0,
                    min(maximum, float(self._control.get(field, 0))),
                )
            if model in MODEL_DEFAULT_MODULES:
                modules = max(
                    1,
                    min(6, int(float(self._control.get(f"venus_{name}_packs", 2)))),
                )
                self._control[f"venus_{name}_packs"] = float(modules)
                self._control[f"nennkapazitaet_{name}_kwh"] = nominal_capacity(
                    model, modules
                )

    def _migrate_storage_reserves(self, loaded_control: dict[str, Any]) -> None:
        """Split the former shared reserve without changing its total energy."""
        keys = [f"mindestreserve_{slot.lower()}_kwh" for slot in self.enabled_models]
        if not keys or any(key in loaded_control for key in keys):
            return

        legacy = max(0.0, float(self._control.get("mindestreserve", 2.0)))
        capacities = {
            slot: max(
                0.1,
                float(self._control.get(f"nennkapazitaet_{slot.lower()}_kwh", 1.0)),
            )
            for slot in self.enabled_models
        }
        total_capacity = sum(capacities.values())
        remaining = round(legacy, 1)
        for index, slot in enumerate(self.enabled_models):
            key = f"mindestreserve_{slot.lower()}_kwh"
            if index == len(self.enabled_models) - 1:
                value = remaining
            else:
                value = round(legacy * capacities[slot] / total_capacity, 1)
                remaining = round(max(0.0, remaining - value), 1)
            self._control[key] = value

    async def async_set_mode(self, mode: str) -> None:
        """Set the native operating mode after validating active control."""
        if mode not in {"Aus", "Beobachten", "Automatik"}:
            raise HomeAssistantError("Unbekannte Betriebsart")
        if mode == "Automatik":
            current = self.data or self._collect_data()
            active_legacy = [
                entity_id
                for entity_id in LEGACY_CONTROLLER_ENTITIES
                if (
                    (state := self.hass.states.get(entity_id)) is not None
                    and state.state == "on"
                )
            ]
            if active_legacy:
                raise HomeAssistantError(
                    "Steuerung nicht aktiviert: bisherige Automation ist noch an: "
                    + ", ".join(active_legacy)
                )
            if not current.get("daten_gueltig") or not current.get("planung_aktiv"):
                raise HomeAssistantError(
                    "Steuerung nicht aktiviert: Daten oder Planung sind ungültig"
                )
            self._last_write_error = None
        previous_mode = self._control.get("mode")
        if previous_mode == "Automatik" and mode != "Automatik":
            # Calculate and apply the planner's saved-value restoration once
            # before write access is finally dormant.
            self._control["mode"] = "Aus"
            release_result = self._collect_data()
            await self._async_apply_control(release_result)
        self._control["mode"] = mode
        self._schedule_state_save()
        await self.async_request_refresh()

    async def async_set_control(self, key: str, value: Any) -> None:
        """Update one native option and persist it."""
        if key not in CONTROL_DEFAULTS or key == "mode":
            raise HomeAssistantError("Unbekannte Einstellung")
        self._control[key] = value
        if key in {"venus_a_packs", "venus_d_packs", "venus_e_packs"}:
            self._sync_model_controls()
        self._schedule_state_save()
        if key in {"manuell_a_aktiv", "manuell_d_aktiv", "manuell_e_aktiv"}:
            await self._async_update_manual_notification()
        await self.async_request_refresh()

    async def async_request_action(self, request: str) -> None:
        """Queue one native calibration or acknowledgement action."""
        valid = {"cancel", "ack"}
        for model in self.enabled_models:
            name = model.lower()
            valid.update({f"cal_{name}", f"cal_{name}_tomorrow", f"cancel_{name}"})
        if request not in valid:
            raise HomeAssistantError("Unbekannte Aktion")
        if request == "ack":
            for model in self.enabled_models:
                self._control[f"schreibfehler_{model.lower()}"] = 0
            self._last_write_error = None
            self._schedule_state_save()
            await self._async_dismiss_notification("speicher_ladelogik_schreibfehler")
            await self._async_dismiss_notification("speicher_ladelogik_ladereaktion")
            await self.async_request_refresh()
            return
        if request != "ack" and not self.write_enabled:
            raise HomeAssistantError(
                "Kalibrieraktionen sind nur in der Betriebsart Automatik möglich"
            )
        if request.startswith("cal_"):
            name = request.split("_", 2)[1]
            self._control[f"kalibrierung_{name}_freigegeben"] = True
            self._control[f"kalibrierung_{name}_laden_sperren"] = True
        elif request.startswith("cancel_"):
            name = request.rsplit("_", 1)[1]
            self._control[f"kalibrierung_{name}_freigegeben"] = False
            self._control[f"kalibrierung_{name}_laden_sperren"] = False
        elif request == "cancel":
            for model in self.enabled_models:
                name = model.lower()
                self._control[f"kalibrierung_{name}_freigegeben"] = False
                self._control[f"kalibrierung_{name}_laden_sperren"] = False
        self._pending_request = request
        self._schedule_state_save()
        await self.async_request_refresh()

    def _schedule_state_save(self) -> None:
        """Persist controls, sessions and stability with write coalescing."""
        payload = {"control": self._control, "stability": self._stored_stability}
        self._stability_store.async_delay_save(lambda: payload, 2)

    async def _async_load_state(self) -> None:
        """Load native state and import legacy helpers once."""
        if self._state_loaded:
            return
        stored = await self._stability_store.async_load()
        loaded_control: dict[str, Any] = {}
        if isinstance(stored, dict) and "control" in stored:
            loaded_control = dict(stored.get("control", {}))
            self._control.update(loaded_control)
            self._stored_stability = dict(stored.get("stability", {}))
        else:
            # One-time migration. The first RC deliberately starts in
            # Beobachten; all harmless values and active calibration state are
            # imported when their old helpers still exist.
            for entity_id, key in HELPER_TO_CONTROL.items():
                resolved = self._resolve_entity(entity_id)
                state = self.hass.states.get(resolved) if resolved else None
                if state is None:
                    continue
                if entity_id.startswith("input_boolean."):
                    self._control[key] = state.state == "on"
                elif entity_id.startswith("input_number."):
                    value = as_number(state.state)
                    if value is not None:
                        self._control[key] = value
                elif is_usable_state(state.state):
                    self._control[key] = state.state
            for entity_id in (
                "sensor.speicher_ladelogik_lernspeicher",
                "sensor.pv_ladelogik_lernspeicher",
            ):
                state = self.hass.states.get(entity_id)
                if state is not None and state.attributes:
                    self._control["lernspeicher"] = dict(state.attributes)
                    break
            self._control["mode"] = "Beobachten"
            self._control["migrated_from_legacy"] = True
        self._sync_model_controls()
        self._migrate_storage_reserves(loaded_control)
        self._state_loaded = True
        self._last_plan = self._stored_stability or None
        self._schedule_state_save()
        await self._async_update_manual_notification()

    async def _async_update_data(self) -> dict[str, Any]:
        await self._async_load_state()
        request = self._pending_request
        self._pending_request = "tick"
        result = self._collect_data(request=request)
        if self.write_enabled:
            try:
                await self._async_apply_control(result)
            except Exception as err:  # noqa: BLE001 - never lose coordinator data
                self._last_write_error = f"Steuerzyklus fehlgeschlagen: {err}"
                _LOGGER.exception("Registersteuerung konnte nicht ausgeführt werden")
            result = self._collect_data()
        await self._async_update_calibration_due_notification(result)
        await self._async_update_problem_notification(result)
        return result

    @callback
    def async_handle_state_change(self, event: Event) -> None:
        """Refresh immediately when a configured entity changes."""
        entity_id = event.data.get("entity_id")
        if self.write_enabled:
            self.hass.async_create_task(self.async_request_refresh())
        else:
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
        return [
            self._snapshot(entity) for entity in entities if isinstance(entity, str)
        ]

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

    def _efficiency(self, ac_key: str, dc_key: str) -> dict[str, Any]:
        """Calculate direction-aware instantaneous conversion efficiency."""
        ac = self._numeric(ac_key, power=True)
        dc = self._numeric(dc_key, power=True)
        return conversion_metrics(ac, dc)

    def _control_timestamp(self, key: str) -> float | None:
        value = self._control.get(key)
        numeric = as_number(value)
        if numeric is not None:
            return numeric
        parsed = dt_util.parse_datetime(str(value)) if value else None
        return parsed.timestamp() if parsed is not None else None

    def _collect_data(self, request: str = "tick") -> dict[str, Any]:
        sources: dict[str, list[dict[str, Any]]] = {}
        configured_source_keys = [
            key
            for slot in self.enabled_models
            for key in SLOT_FIELDS[slot].values()
        ]
        for key in (*COMMON_KEYS, *configured_source_keys):
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
        mppt_sum_w = (
            sum(value for value in mppt_values if value is not None)
            if (mppt_complete and all(value is not None for value in mppt_values))
            else None
        )

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

        common_ready = all(
            self._key_available(key) for key in REQUIRED_COMMON_KEYS
        ) and (pv_ac_w is not None or mppt_sum_w is not None)
        required_by_model = {
            slot: tuple(
                SLOT_FIELDS[slot][field]
                for field in (
                    "soc",
                    "ac_power",
                    "charge_limit",
                    "discharge_limit",
                    "auto_target",
                    "active",
                )
            )
            for slot in self.enabled_models
        }
        ready = {
            model: all(self._key_available(key) for key in required_by_model[model])
            for model in self.enabled_models
        }
        efficiency_keys = {
            slot: (
                SLOT_FIELDS[slot]["ac_power"],
                SLOT_FIELDS[slot]["dc_power"],
            )
            for slot in self.enabled_models
        }
        efficiencies = {
            model: self._efficiency(*efficiency_keys[model])
            for model in self.enabled_models
        }
        now_ts = dt_util.utcnow().timestamp()
        last_success = {
            battery: self._control_timestamp(
                f"kalibrierung_{battery.lower()}_letzter_erfolg"
            )
            for battery in self.enabled_models
        }
        next_due = {
            battery: stamp + 30 * 86400 if stamp is not None else None
            for battery, stamp in last_success.items()
        }

        result = {
            "version": VERSION,
            "betriebsart": self._control.get("mode", "Beobachten"),
            "schreibzugriffe_aktiv": self.write_enabled,
            "daten_gueltig_gemeinsam": common_ready,
            "daten_gueltig_venus_a": ready.get("A", True),
            "daten_gueltig_venus_d": ready.get("D", True),
            "daten_gueltig_venus_e": ready.get("E", True),
            "daten_gueltig": common_ready and all(ready.values()),
            "pv_planungswert_w": round(pv_plan_w) if pv_plan_w is not None else None,
            "pv_planungswert_quelle": pv_source,
            "pv_ac_w": round(pv_ac_w) if pv_ac_w is not None else None,
            "pv_mppt_summe_dc_w": round(mppt_sum_w) if mppt_sum_w is not None else None,
            "soc_venus_a": self._numeric(CONF_A_SOC) if "A" in self.enabled_models else None,
            "soc_venus_d": self._numeric(CONF_D_SOC) if "D" in self.enabled_models else None,
            "soc_venus_e": self._numeric(CONF_E_SOC) if "E" in self.enabled_models else None,
            "ac_leistung_venus_a_w": self._numeric(CONF_A_AC_POWER, power=True) if "A" in self.enabled_models else None,
            "ac_leistung_venus_d_w": self._numeric(CONF_D_AC_POWER, power=True) if "D" in self.enabled_models else None,
            "ac_leistung_venus_e_w": self._numeric(CONF_E_AC_POWER, power=True) if "E" in self.enabled_models else None,
            "wirkungsgrad_venus_a": efficiencies.get("A", {}),
            "wirkungsgrad_venus_d": efficiencies.get("D", {}),
            "wirkungsgrad_venus_e": efficiencies.get("E", {}),
            "fehlende_entitaeten": missing,
            "warnungen": [f"Nicht verfügbar: {entity}" for entity in missing],
            "quellen_gesamt": len(self.source_entities),
            "quellen_verfuegbar": len(self.source_entities) - len(missing),
            "quellen": sources,
            "letzter_schreibfehler": self._last_write_error,
            "letzter_schreibzugriff_ts": self._last_write_ts,
            "letzte_schreibergebnisse": self._last_write_results,
            "aktivierte_speicher": list(self.enabled_models),
        }
        for model in self.enabled_models:
            name = model.lower()
            result[f"kalibrierung_letzter_erfolg_{name}_ts"] = last_success[model]
            result[f"kalibrierung_naechste_faelligkeit_{name}_ts"] = next_due[model]
            result[f"kalibrierung_faellig_{name}"] = (
                next_due[model] is not None and now_ts >= next_due[model]
            )

        try:
            calculation = calculate(
                self.hass,
                self.config,
                self._last_plan,
                request=request,
                control=self._control,
            )
            plan = calculation.get("plan", {})
            calibration = calculation.get("calibration", {})
            result.update(
                {
                    "planung_aktiv": True,
                    "planungsfehler": None,
                    "plan": plan,
                    "calibration": calibration,
                    "proposed_commands": calculation.get("proposed_commands", []),
                    "control_output": calculation,
                }
            )
            self._last_plan = plan
            stability = {
                key: plan.get(key)
                for key in _STABILITY_KEYS
            }
            if stability != self._stored_stability:
                self._stored_stability = stability
                self._schedule_state_save()
        except Exception as err:  # noqa: BLE001 - keep observation sensors alive
            _LOGGER.exception("Planung konnte nicht berechnet werden")
            result.update(
                {
                    "planung_aktiv": False,
                    "planungsfehler": str(err),
                    "plan": {},
                    "calibration": {},
                    "proposed_commands": [],
                    "control_output": {},
                }
            )
        return result

    def _resolve_entity(self, entity_id: str) -> str | None:
        """Resolve a current helper or its V2.2.1 compatibility entity."""
        if self.hass.states.get(entity_id) is not None:
            return entity_id
        legacy = legacy_entity_id(entity_id)
        if legacy is not None and self.hass.states.get(legacy) is not None:
            return legacy
        return None

    async def _async_set_helper(self, entity_id: str, value: Any) -> bool:
        """Set integration-owned state, with legacy helper fallback for migration."""
        control_key = HELPER_TO_CONTROL.get(entity_id)
        if control_key is not None:
            if self._control.get(control_key) != value:
                self._control[control_key] = value
                self._schedule_state_save()
            return True
        resolved = self._resolve_entity(entity_id)
        if resolved is None:
            return False
        state = self.hass.states.get(resolved)
        domain = resolved.split(".", 1)[0]
        if state is not None:
            if domain == "input_number":
                try:
                    if abs(float(state.state) - float(value)) < 0.001:
                        return True
                except (TypeError, ValueError):
                    pass
            elif domain == "input_boolean":
                expected = "on" if bool(value) else "off"
                if state.state == expected:
                    return True
            elif str(state.state) == str(value):
                return True
        if domain in {"input_text", "input_number"}:
            await self.hass.services.async_call(
                domain,
                "set_value",
                {"entity_id": resolved, "value": value},
                blocking=True,
            )
            return True
        if domain == "input_datetime":
            await self.hass.services.async_call(
                domain,
                "set_datetime",
                {"entity_id": resolved, "timestamp": value},
                blocking=True,
            )
            return True
        if domain == "input_boolean":
            await self.hass.services.async_call(
                domain,
                "turn_on" if bool(value) else "turn_off",
                {"entity_id": resolved},
                blocking=True,
            )
            return True
        return False

    def _control_allowed(self, battery: str, restore: bool) -> bool:
        """Recheck the device-side control gates immediately before a write."""
        keys = {
            "A": (CONF_A_AUTO_TARGET, CONF_A_ACTIVE, CONF_A_CHARGE_OVERRIDE),
            "D": (CONF_D_AUTO_TARGET, CONF_D_ACTIVE, CONF_D_CHARGE_OVERRIDE),
            "E": (CONF_E_AUTO_TARGET, CONF_E_ACTIVE, CONF_E_CHARGE_OVERRIDE),
        }
        auto_key, active_key, override_key = keys[battery]
        auto = self.hass.states.get(self.config.get(auto_key, ""))
        active = self.hass.states.get(self.config.get(active_key, ""))
        override_id = self.config.get(override_key)
        override = self.hass.states.get(override_id) if override_id else None
        plan = (self.data or {}).get("plan", {})
        return bool(
            (restore or plan.get("regelung_aktiv"))
            and auto is not None
            and auto.state == "on"
            and active is not None
            and active.state == "on"
            and (override is None or override.state != "on")
        )

    async def _async_confirm_number(
        self, entity_id: str, target: float, timeout: float = 20.0
    ) -> bool:
        """Wait until Home Assistant reports the requested number value."""
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            state = self.hass.states.get(entity_id)
            if state is not None and not write_needed(state.state, target):
                return True
            await asyncio.sleep(0.25)
        return False

    async def _async_write_number(self, command: dict[str, Any]) -> dict[str, Any]:
        """Validate, write and confirm one permitted register command."""
        battery = str(command.get("battery", ""))
        entity_id = str(command.get("entity", ""))
        target = command.get("value")
        restore = bool(command.get("restore"))
        allowed = {
            self.config.get(CONF_A_CHARGE_LIMIT),
            self.config.get(CONF_A_DISCHARGE_LIMIT),
            self.config.get(CONF_D_CHARGE_LIMIT),
            self.config.get(CONF_D_DISCHARGE_LIMIT),
            self.config.get(CONF_E_CHARGE_LIMIT),
            self.config.get(CONF_E_DISCHARGE_LIMIT),
        }
        result = {
            "entity": entity_id,
            "value": target,
            "battery": battery,
            "restore": restore,
            "ok": False,
            "written": False,
        }
        if battery not in self.enabled_models or entity_id not in allowed:
            result["error"] = "Nicht freigegebene Stellgröße"
            return result
        if not self._control_allowed(battery, restore):
            result["error"] = "Steuerfreigabe unmittelbar vor Schreiben ungültig"
            return result
        state = self.hass.states.get(entity_id)
        if state is None:
            result["error"] = "Stellgröße nicht verfügbar"
            return result
        error = validate_number_target(
            current=state.state,
            minimum=state.attributes.get("min"),
            maximum=state.attributes.get("max"),
            step=state.attributes.get("step"),
            target=target,
        )
        if error is not None:
            result["error"] = error
            return result
        if not write_needed(state.state, target):
            result["ok"] = True
            return result
        try:
            await self.hass.services.async_call(
                "number",
                "set_value",
                {"entity_id": entity_id, "value": target},
                blocking=True,
            )
            result["written"] = True
            await self.hass.services.async_call(
                "homeassistant",
                "update_entity",
                {"entity_id": entity_id},
                blocking=True,
            )
        except Exception as err:  # noqa: BLE001 - report a failed device write
            result["error"] = f"Dienstaufruf fehlgeschlagen: {err}"
            return result
        result["ok"] = await self._async_confirm_number(entity_id, float(target))
        if not result["ok"]:
            result["error"] = "Registerwert innerhalb 20 Sekunden nicht bestätigt"
        return result

    async def _async_update_failure_counters(
        self, attempted: dict[str, bool], successful: dict[str, bool]
    ) -> None:
        """Maintain the existing per-battery write-failure safety counters."""
        values: dict[str, int] = {}
        for battery in self.enabled_models:
            key = "schreibfehler_" + battery.lower()
            previous = int(float(self._control.get(key, 0)))
            value = previous
            if attempted[battery]:
                value = 0 if successful[battery] else min(3, previous + 1)
                self._control[key] = value
            values[battery] = value
        self._schedule_state_save()

    async def _async_safe_stop(self) -> None:
        """Set charge limits to zero if an active controller loses its plan."""
        charge_keys = {
            "A": CONF_A_CHARGE_LIMIT,
            "D": CONF_D_CHARGE_LIMIT,
            "E": CONF_E_CHARGE_LIMIT,
        }
        commands = [
            {
                "entity": self.config.get(charge_keys[battery]),
                "value": 0,
                "battery": battery,
                "restore": True,
            }
            for battery in self.enabled_models
        ]
        results = []
        for command in commands:
            results.append(await self._async_write_number(command))
        self._last_write_results = results
        self._last_write_error = (
            "Planung ausgefallen; Ladegrenzen wurden auf 0 W gesetzt"
        )

    async def _async_notification(
        self, notification_id: str, title: str, message: str
    ) -> None:
        """Create or update one persistent control notification."""
        await self.hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "notification_id": notification_id,
                "title": title,
                "message": message,
            },
            blocking=True,
        )

    async def _async_mobile_notification(self, title: str, message: str) -> None:
        """Optionally mirror a new problem to one configured mobile notify service."""
        target = str(self.config.get(CONF_MOBILE_NOTIFY_SERVICE, "")).strip()
        if not target:
            return
        if target.startswith("notify."):
            service = target.split(".", 1)[1]
        else:
            service = target
        if not service or not all(char.isalnum() or char == "_" for char in service):
            _LOGGER.warning("Ungültiger mobiler Benachrichtigungsdienst: %s", target)
            return
        try:
            await self.hass.services.async_call(
                "notify",
                service,
                {"title": title, "message": message},
                blocking=True,
            )
        except Exception as err:  # noqa: BLE001 - push must never block control
            _LOGGER.warning("Mobile Benachrichtigung fehlgeschlagen: %s", err)

    async def _async_update_problem_notification(self, data: dict[str, Any]) -> None:
        """Report planner failures immediately and stale/invalid data after 5 min."""
        now = dt_util.utcnow().timestamp()
        planner_error = data.get("planungsfehler")
        missing = tuple(data.get("fehlende_entitaeten", ()))
        if planner_error:
            signature = "Planungsfehler: " + str(planner_error)
            ready = True
        elif not data.get("daten_gueltig", False):
            signature = "Ungültige Daten: " + (", ".join(missing) or "Ursache unbekannt")
            if signature != self._problem_signature:
                self._problem_started_ts = now
            ready = now - (self._problem_started_ts or now) >= 300
        else:
            self._problem_signature = None
            self._problem_started_ts = None
            self._mobile_problem_signature = None
            await self._async_dismiss_notification("speicher_ladelogik_problem")
            return

        changed = signature != self._problem_signature
        if changed:
            self._problem_signature = signature
            if planner_error:
                self._problem_started_ts = now
        if not ready:
            return
        title = "Speicher-Ladelogik – Problem erkannt"
        message = signature + "\n\nDie Automatik schreibt ohne gültigen Plan keine neuen Ladegrenzen."
        await self._async_notification(
            "speicher_ladelogik_problem",
            title,
            message,
        )
        if signature != self._mobile_problem_signature:
            await self._async_mobile_notification(title, message)
            self._mobile_problem_signature = signature

    async def _async_dismiss_notification(self, notification_id: str) -> None:
        """Dismiss a persistent notification without failing the control cycle."""
        try:
            await self.hass.services.async_call(
                "persistent_notification",
                "dismiss",
                {"notification_id": notification_id},
                blocking=True,
            )
        except Exception:  # noqa: BLE001 - a missing notification is harmless
            return

    async def _async_update_manual_notification(self) -> None:
        """Keep an unmistakable reminder while a manual storage mode is active."""
        active = [
            battery
            for battery in self.enabled_models
            if self._control.get(f"manuell_{battery.lower()}_aktiv")
        ]
        if not active:
            await self._async_dismiss_notification("speicher_ladelogik_manuell")
            return
        await self._async_notification(
            "speicher_ladelogik_manuell",
            "Speicher-Ladelogik – Handbetrieb aktiv",
            "Handbetrieb ist für " + "/".join(self.storage_name(slot) for slot in active)
            + " dauerhaft aktiv. Der jeweils andere Speicher läuft weiter im Fahrplan. "
            "Bitte nach dem Einsatz wieder ausschalten.",
        )

    async def _async_update_calibration_due_notification(self, data: dict[str, Any]) -> None:
        """Notify once when a known successful calibration becomes 30 days old."""
        due = tuple(
            battery
            for battery in self.enabled_models
            if data.get(f"kalibrierung_faellig_{battery.lower()}")
        )
        if due == self._due_notified:
            return
        self._due_notified = due
        if not due:
            await self._async_dismiss_notification("speicher_ladelogik_kalibrierung_faellig")
            return
        await self._async_notification(
            "speicher_ladelogik_kalibrierung_faellig",
            "Speicher-Ladelogik – Kalibrierung fällig",
            "Seit der letzten erfolgreichen Kalibrierung von "
            + "/".join(self.storage_name(slot) for slot in due)
            + " sind mindestens 30 Tage vergangen. Es wird kein Auftrag automatisch gestartet.",
        )

    async def _async_apply_control(self, result: dict[str, Any]) -> None:
        """Apply one calculated cycle with backups, checks and confirmation."""
        async with self._write_lock:
            output = result.get("control_output", {})
            if not result.get("planung_aktiv") or not output:
                await self._async_safe_stop()
                return

            if output.get("ack"):
                failure_entities = [
                    "input_number.speicher_ladelogik_schreibfehler",
                    *(
                        "input_number.speicher_ladelogik_schreibfehler_"
                        + model.lower()
                        for model in self.enabled_models
                    ),
                ]
                for entity_id in failure_entities:
                    await self._async_set_helper(entity_id, 0)
                self._last_write_error = None
                await self._async_dismiss_notification(
                    "speicher_ladelogik_schreibfehler"
                )
                await self._async_dismiss_notification(
                    "speicher_ladelogik_ladereaktion"
                )

            if isinstance(output.get("learning"), dict):
                self._control["lernspeicher"] = output["learning"]
                self._schedule_state_save()

            if output.get("save_backup"):
                await self._async_set_helper(BACKUP_ENTITY, output["save_backup"])
            if output.get("save_cal_backup"):
                await self._async_set_helper(
                    CAL_BACKUP_ENTITY, output["save_cal_backup"]
                )
            await self._async_set_helper(SESSION_ENTITY, output.get("session", ""))
            await self._async_set_helper(QUEUE_ENTITY, output.get("queue", ""))

            by_battery = {battery: [] for battery in self.enabled_models}
            for command in output.get("proposed_commands", []):
                battery = command.get("battery")
                if battery in by_battery:
                    by_battery[battery].append(command)
            results: list[dict[str, Any]] = []
            attempted = {battery: False for battery in self.enabled_models}
            successful = {battery: True for battery in self.enabled_models}
            for battery in output.get("write_order", self.enabled_models):
                for command in by_battery.get(battery, []):
                    if not successful[battery]:
                        break
                    attempted[battery] = True
                    write_result = await self._async_write_number(command)
                    results.append(write_result)
                    successful[battery] = bool(write_result["ok"])

            await self._async_update_failure_counters(attempted, successful)
            all_ok = all(successful.values())
            if all_ok and output.get("clear_backup"):
                await self._async_set_helper(BACKUP_ENTITY, "")
            if all_ok and output.get("clear_cal_backup"):
                await self._async_set_helper(CAL_BACKUP_ENTITY, "")

            plan = output.get("plan", {})
            release = bool(
                all_ok
                and plan.get("regelung_aktiv")
                and any(
                    plan.get(
                        f"soll_ladegrenze_venus_{model.lower()}_w", 0
                    ) > 0
                    for model in self.enabled_models
                )
            )
            await self._async_set_helper(
                "input_boolean.speicher_ladelogik_laden_freigegeben", release
            )
            if output.get("finish") and all_ok:
                battery = str(output.get("calibration", {}).get("batterie", ""))
                name = battery.lower()
                if battery in self.enabled_models:
                    await self._async_set_helper(
                        "input_datetime.speicher_ladelogik_kalibrierung_"
                        f"{name}_letzter_erfolg",
                        dt_util.utcnow().timestamp(),
                    )
                    await self._async_set_helper(
                        "input_boolean.speicher_ladelogik_kalibrierung_"
                        f"{name}_erfolg_bekannt",
                        True,
                    )
                    await self._async_set_helper(
                        "input_number.speicher_ladelogik_kalibrierung_"
                        f"{name}_letzte_energie",
                        output.get("calibration", {}).get("energie_ac_kwh", 0),
                    )
                for entity_id in output.get("reset_after_calibration", []):
                    await self._async_set_helper(entity_id, False)

            if output.get("capture_drift") and all_ok:
                calibration = output.get("calibration", {})
                drift_fields = {
                    "A": (
                        ("a_p1", "drift_a_p1_mv"),
                        ("a_p2", "drift_a_p2_mv"),
                    ),
                    "E": (("e", "drift_e_mv"),),
                    "D": (
                        ("d_p1", "drift_d_p1_mv"),
                        ("d_p2", "drift_d_p2_mv"),
                    ),
                }
                battery = calibration.get("batterie")
                for helper_suffix, attribute in drift_fields.get(battery, ()):
                    value = calibration.get(attribute)
                    if value is not None:
                        await self._async_set_helper(
                            "input_number.speicher_ladelogik_kalibrierung_"
                            f"{helper_suffix}_letzte_drift",
                            round(float(value)),
                        )

            event_data = {
                "plan": plan,
                "calibration": output.get("calibration", {}),
                "learning": output.get("learning", {}),
                "journal_event": output.get("journal_event", False),
                "writes_ok": all_ok,
            }
            for model in ("A", "D", "E"):
                event_data[f"writes_{model.lower()}"] = successful.get(model, True)
            self.hass.bus.async_fire("speicher_ladelogik_auswertung", event_data)
            self.hass.bus.async_fire("pv_ladelogik_v2_auswertung", event_data)

            if output.get("notify"):
                await self._async_notification(
                    "speicher_ladelogik_kalibrierung",
                    "Speicher-Ladelogik – Kalibrierung",
                    str(output["notify"]),
                )
            if output.get("reaction_newly_blocked"):
                batteries = "/".join(
                    self.storage_name(slot)
                    for slot in output["reaction_newly_blocked"]
                )
                await self._async_notification(
                    "speicher_ladelogik_ladereaktion",
                    "Speicher-Ladelogik – Ladeleistung nicht bestätigt",
                    batteries
                    + " hat nach der Ladefreigabe keine frische "
                    "AC-Rückmeldung geliefert.",
                )

            errors = [item.get("error") for item in results if not item.get("ok")]
            if results:
                self._last_write_results = results
                self._last_write_ts = dt_util.utcnow().timestamp()
                self._last_write_error = (
                    "; ".join(error for error in errors if error) or None
                )
            if errors:
                blocked = [
                    battery
                    for battery in self.enabled_models
                    if int(self._control.get(f"schreibfehler_{battery.lower()}", 0)) >= 3
                ]
                await self._async_notification(
                    "speicher_ladelogik_schreibfehler",
                    "Speicher-Ladelogik – Grenzwert nicht bestätigt",
                    (self._last_write_error or "Unbekannter Schreibfehler")
                    + ("\n\nGesperrt bis zur Quittierung: " + "/".join(self.storage_name(slot) for slot in blocked)
                       if blocked else ""),
                )
            elif results:
                await self._async_dismiss_notification(
                    "speicher_ladelogik_schreibfehler"
                )
