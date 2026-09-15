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

from .compat import compatibility_entity_ids, legacy_entity_id
from .const import (
    COMMON_KEYS,
    CONF_A_AC_POWER,
    CONF_A_ACTIVE,
    CONF_A_AUTO_TARGET,
    CONF_A_CHARGE_LIMIT,
    CONF_A_CHARGE_OVERRIDE,
    CONF_A_DISCHARGE_LIMIT,
    CONF_A_SOC,
    CONF_E_AC_POWER,
    CONF_E_ACTIVE,
    CONF_E_AUTO_TARGET,
    CONF_E_CHARGE_LIMIT,
    CONF_E_CHARGE_OVERRIDE,
    CONF_E_DISCHARGE_LIMIT,
    CONF_E_SOC,
    CONF_MPPT_SENSORS,
    CONF_PV_AC,
    DOMAIN,
    REQUIRED_A_KEYS,
    REQUIRED_COMMON_KEYS,
    REQUIRED_E_KEYS,
    SHADOW_TRACKED_ENTITIES,
    UPDATE_INTERVAL_SECONDS,
    VENUS_A_KEYS,
    VENUS_E_KEYS,
    VERSION,
)
from .control import (
    BACKUP_ENTITY,
    CAL_BACKUP_ENTITY,
    CONTROL_HELPERS,
    LEGACY_CONTROLLER_ENTITIES,
    QUEUE_ENTITY,
    REQUEST_ENTITIES,
    SESSION_ENTITY,
    validate_number_target,
    write_needed,
)
from .helpers import as_number, is_usable_state, power_in_watts
from .planner_adapter import calculate, compare_with_legacy

_LOGGER = logging.getLogger(__name__)

_STABILITY_STORAGE_VERSION = 1
_STABILITY_KEYS = tuple(
    field
    for name in ("a", "e")
    for field in (
        f"ziel_venus_{name}_erreicht",
        f"ziel_venus_{name}_latch_soc",
        f"fahrplan_ladegrenze_stabil_venus_{name}_w",
    )
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
        self.config = dict(entry.data)
        self._last_shadow_plan: dict[str, Any] | None = None
        self._stored_stability: dict[str, Any] = {}
        self._write_enabled = False
        self._write_lock = asyncio.Lock()
        self._pending_request = "tick"
        self._last_write_error: str | None = None
        self._last_write_ts: float | None = None
        self._last_write_results: list[dict[str, Any]] = []
        self._stability_store: Store[dict[str, Any]] = Store(
            hass,
            _STABILITY_STORAGE_VERSION,
            f"{DOMAIN}.{entry.entry_id}.stability",
        )

    @property
    def source_entities(self) -> list[str]:
        """Return every entity selected in the config flow once."""
        entities: list[str] = []
        for value in self.config.values():
            candidates = value if isinstance(value, list) else [value]
            for candidate in candidates:
                if isinstance(candidate, str) and "." in candidate:
                    entities.append(candidate)
        return list(dict.fromkeys(entities))

    @property
    def tracked_entities(self) -> list[str]:
        """Return sources and legacy helper entities that trigger recalculation."""
        shadow_entities = [
            *SHADOW_TRACKED_ENTITIES,
            *compatibility_entity_ids(SHADOW_TRACKED_ENTITIES),
        ]
        return list(
            dict.fromkeys(
                [*self.source_entities, *shadow_entities, *REQUEST_ENTITIES]
            )
        )

    @property
    def write_enabled(self) -> bool:
        """Return whether this runtime is allowed to write device registers."""
        return self._write_enabled

    async def async_set_write_enabled(self, enabled: bool) -> None:
        """Enable or disable guarded register control for this HA runtime."""
        if enabled:
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
            missing_helpers = [
                entity_id
                for entity_id in CONTROL_HELPERS
                if self._resolve_entity(entity_id) is None
            ]
            if missing_helpers:
                raise HomeAssistantError(
                    "Steuerung nicht aktiviert: Zustandshelfer fehlen: "
                    + ", ".join(missing_helpers)
                )
            if not current.get("daten_gueltig") or not current.get(
                "schattenplanung_aktiv"
            ):
                raise HomeAssistantError(
                    "Steuerung nicht aktiviert: Daten oder Planung sind ungültig"
                )
            self._write_enabled = True
            self._last_write_error = None
            await self.async_request_refresh()
            return

        self._write_enabled = False
        self._pending_request = "tick"
        self.async_set_updated_data(self._collect_data())

    async def _async_update_data(self) -> dict[str, Any]:
        if self._last_shadow_plan is None:
            stored = await self._stability_store.async_load()
            if isinstance(stored, dict):
                self._stored_stability = stored
                self._last_shadow_plan = stored
        request = self._pending_request
        self._pending_request = "tick"
        result = self._collect_data(request=request)
        if self._write_enabled:
            try:
                await self._async_apply_control(result)
            except Exception as err:  # noqa: BLE001 - never lose coordinator data
                self._last_write_error = f"Steuerzyklus fehlgeschlagen: {err}"
                _LOGGER.exception("Registersteuerung konnte nicht ausgeführt werden")
            result = self._collect_data()
        return result

    @callback
    def async_handle_state_change(self, event: Event) -> None:
        """Refresh immediately when a configured entity changes."""
        entity_id = event.data.get("entity_id")
        request = REQUEST_ENTITIES.get(entity_id)
        if request is not None and self._write_enabled:
            self._pending_request = request
        if self._write_enabled:
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

    def _collect_data(self, request: str = "tick") -> dict[str, Any]:
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
        a_ready = all(self._key_available(key) for key in REQUIRED_A_KEYS)
        e_ready = all(self._key_available(key) for key in REQUIRED_E_KEYS)

        result = {
            "version": VERSION,
            "betriebsart": "Steuerung" if self._write_enabled else "Beobachten",
            "schreibzugriffe_aktiv": self._write_enabled,
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
            "quellen_gesamt": len(self.source_entities),
            "quellen_verfuegbar": len(self.source_entities) - len(missing),
            "quellen": sources,
            "letzter_schreibfehler": self._last_write_error,
            "letzter_schreibzugriff_ts": self._last_write_ts,
            "letzte_schreibergebnisse": self._last_write_results,
        }

        try:
            shadow = calculate(
                self.hass,
                self.config,
                self._last_shadow_plan,
                request=request,
            )
            shadow_plan = shadow.get("plan", {})
            shadow_calibration = shadow.get("calibration", {})
            result.update(
                {
                    "schattenplanung_aktiv": True,
                    "schattenplanung_fehler": None,
                    "shadow_plan": shadow_plan,
                    "shadow_calibration": shadow_calibration,
                    "shadow_comparison": compare_with_legacy(
                        self.hass, shadow_plan, shadow_calibration
                    ),
                    "shadow_proposed_commands": shadow.get("proposed_commands", []),
                    "control_output": shadow,
                }
            )
            self._last_shadow_plan = shadow_plan
            stability = {
                key: shadow_plan.get(key)
                for key in _STABILITY_KEYS
            }
            if stability != self._stored_stability:
                self._stored_stability = stability
                self._stability_store.async_delay_save(
                    lambda: self._stored_stability,
                    10,
                )
        except Exception as err:  # noqa: BLE001 - keep observation sensors alive
            _LOGGER.exception("Schattenplanung konnte nicht berechnet werden")
            result.update(
                {
                    "schattenplanung_aktiv": False,
                    "schattenplanung_fehler": str(err),
                    "shadow_plan": {},
                    "shadow_calibration": {},
                    "shadow_comparison": {
                        "available": False,
                        "matches": None,
                        "funktional_passend": None,
                        "fields_compared": 0,
                        "differences": [],
                        "beabsichtigte_abweichungen": 0,
                        "sonstige_abweichungen": 0,
                        "referenz_plan_entitaet": None,
                        "referenz_kalibrierung_entitaet": None,
                    },
                    "shadow_proposed_commands": [],
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
        """Set an existing helper only when its value actually changed."""
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
            "E": (CONF_E_AUTO_TARGET, CONF_E_ACTIVE, CONF_E_CHARGE_OVERRIDE),
        }
        auto_key, active_key, override_key = keys[battery]
        auto = self.hass.states.get(self.config.get(auto_key, ""))
        active = self.hass.states.get(self.config.get(active_key, ""))
        override_id = self.config.get(override_key)
        override = self.hass.states.get(override_id) if override_id else None
        plan = (self.data or {}).get("shadow_plan", {})
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
        if battery not in {"A", "E"} or entity_id not in allowed:
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
        for battery in ("A", "E"):
            entity_id = (
                "input_number.speicher_ladelogik_schreibfehler_"
                + battery.lower()
            )
            resolved = self._resolve_entity(entity_id)
            state = self.hass.states.get(resolved) if resolved else None
            try:
                previous = int(float(state.state)) if state is not None else 0
            except (TypeError, ValueError):
                previous = 0
            value = previous
            if attempted[battery]:
                value = 0 if successful[battery] else min(3, previous + 1)
                await self._async_set_helper(entity_id, value)
            values[battery] = value
        await self._async_set_helper(
            "input_number.speicher_ladelogik_schreibfehler",
            max(values.values()),
        )

    async def _async_safe_stop(self) -> None:
        """Set charge limits to zero if an active controller loses its plan."""
        commands = [
            {
                "entity": self.config.get(CONF_A_CHARGE_LIMIT),
                "value": 0,
                "battery": "A",
                "restore": True,
            },
            {
                "entity": self.config.get(CONF_E_CHARGE_LIMIT),
                "value": 0,
                "battery": "E",
                "restore": True,
            },
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

    async def _async_apply_control(self, result: dict[str, Any]) -> None:
        """Apply one calculated cycle with backups, checks and confirmation."""
        async with self._write_lock:
            output = result.get("control_output", {})
            if not result.get("schattenplanung_aktiv") or not output:
                await self._async_safe_stop()
                return

            if output.get("ack"):
                for entity_id in (
                    "input_number.speicher_ladelogik_schreibfehler",
                    "input_number.speicher_ladelogik_schreibfehler_a",
                    "input_number.speicher_ladelogik_schreibfehler_e",
                ):
                    await self._async_set_helper(entity_id, 0)
                self._last_write_error = None
                await self._async_dismiss_notification(
                    "speicher_ladelogik_schreibfehler"
                )
                await self._async_dismiss_notification(
                    "speicher_ladelogik_ladereaktion"
                )

            if output.get("save_backup"):
                await self._async_set_helper(BACKUP_ENTITY, output["save_backup"])
            if output.get("save_cal_backup"):
                await self._async_set_helper(
                    CAL_BACKUP_ENTITY, output["save_cal_backup"]
                )
            await self._async_set_helper(SESSION_ENTITY, output.get("session", ""))
            await self._async_set_helper(QUEUE_ENTITY, output.get("queue", ""))

            by_battery = {"A": [], "E": []}
            for command in output.get("proposed_commands", []):
                battery = command.get("battery")
                if battery in by_battery:
                    by_battery[battery].append(command)
            results: list[dict[str, Any]] = []
            attempted = {"A": False, "E": False}
            successful = {"A": True, "E": True}
            for battery in output.get("write_order", ("A", "E")):
                for command in by_battery.get(battery, []):
                    if not successful[battery]:
                        break
                    attempted[battery] = True
                    write_result = await self._async_write_number(command)
                    results.append(write_result)
                    successful[battery] = bool(write_result["ok"])

            await self._async_update_failure_counters(attempted, successful)
            all_ok = successful["A"] and successful["E"]
            if all_ok and output.get("clear_backup"):
                await self._async_set_helper(BACKUP_ENTITY, "")
            if all_ok and output.get("clear_cal_backup"):
                await self._async_set_helper(CAL_BACKUP_ENTITY, "")

            plan = output.get("plan", {})
            release = bool(
                all_ok
                and plan.get("regelung_aktiv")
                and (
                    plan.get("soll_ladegrenze_venus_a_w", 0) > 0
                    or plan.get("soll_ladegrenze_venus_e_w", 0) > 0
                )
            )
            await self._async_set_helper(
                "input_boolean.speicher_ladelogik_laden_freigegeben", release
            )
            if output.get("finish") and all_ok:
                battery = str(output.get("calibration", {}).get("batterie", ""))
                name = battery.lower()
                if battery in {"A", "E"}:
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
                "writes_a": successful["A"],
                "writes_e": successful["E"],
            }
            self.hass.bus.async_fire("speicher_ladelogik_auswertung", event_data)
            self.hass.bus.async_fire("pv_ladelogik_v2_auswertung", event_data)

            if output.get("notify"):
                await self._async_notification(
                    "speicher_ladelogik_kalibrierung",
                    "Speicher-Ladelogik – Kalibrierung",
                    str(output["notify"]),
                )
            if output.get("reaction_newly_blocked"):
                batteries = "/".join(output["reaction_newly_blocked"])
                await self._async_notification(
                    "speicher_ladelogik_ladereaktion",
                    "Speicher-Ladelogik – Ladeleistung nicht bestätigt",
                    "Venus "
                    + batteries
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
                await self._async_notification(
                    "speicher_ladelogik_schreibfehler",
                    "Speicher-Ladelogik – Grenzwert nicht bestätigt",
                    self._last_write_error or "Unbekannter Schreibfehler",
                )
            elif results:
                await self._async_dismiss_notification(
                    "speicher_ladelogik_schreibfehler"
                )
