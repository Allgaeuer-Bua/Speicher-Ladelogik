"""Config flow for Speicher-Ladelogik A/E."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    TextSelector,
    TextSelectorConfig,
)

from .const import (
    CONF_A_AC_POWER,
    CONF_A_ACTIVE,
    CONF_A_AUTO_TARGET,
    CONF_A_CHARGE_LIMIT,
    CONF_A_CHARGE_OVERRIDE,
    CONF_A_DC_POWER,
    CONF_A_DISCHARGE_LIMIT,
    CONF_A_MAX_CELL_TEMP,
    CONF_A_MAX_CELL_VOLTAGE,
    CONF_A_MAX_SOC,
    CONF_A_MIN_CELL_TEMP,
    CONF_A_MIN_SOC,
    CONF_A_MPPT_SENSORS,
    CONF_A_PACK_DRIFT,
    CONF_A_PACK_SOC,
    CONF_A_SOC,
    CONF_E_AC_POWER,
    CONF_E_ACTIVE,
    CONF_E_AUTO_TARGET,
    CONF_E_CELL_DRIFT,
    CONF_E_CHARGE_LIMIT,
    CONF_E_CHARGE_OVERRIDE,
    CONF_E_DC_POWER,
    CONF_E_DISCHARGE_LIMIT,
    CONF_E_MAX_CELL_TEMP,
    CONF_E_MAX_CELL_VOLTAGE,
    CONF_E_MAX_SOC,
    CONF_E_MIN_CELL_TEMP,
    CONF_E_MIN_SOC,
    CONF_E_SOC,
    CONF_ENABLED_MODELS,
    CONF_FORECAST_SENSORS,
    CONF_GRID_POWER,
    CONF_HOUSE_POWER,
    CONF_HOUSE_POWER_AVERAGE,
    CONF_MOBILE_NOTIFY_SERVICE,
    CONF_MPPT_SENSORS,
    CONF_NAME,
    CONF_PV_AC,
    CONF_PV_DAILY_ENERGY,
    CONF_STORAGE_INSTANCES,
    DEFAULTS,
    DOMAIN,
)
from .storage import MODEL_DEFAULTS, storage_instances


def _entity(domain: str | list[str], *, multiple: bool = False) -> EntitySelector:
    return EntitySelector(EntitySelectorConfig(domain=domain, multiple=multiple))


class SpeicherLadelogikConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure Speicher-Ladelogik A/E from the UI."""

    VERSION = 3
    MINOR_VERSION = 0

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._storage_models: list[str] = []
        self._storage_instances: list[dict[str, Any]] = []
        self._storage_defaults: list[dict[str, Any]] = []
        self._storage_index = 0
        self._reconfigure_entry: config_entries.ConfigEntry | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Return the options flow for notification settings."""
        return SpeicherLadelogikOptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Configure common sources."""
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            self._storage_models = ["A", "E"]
            self._data.update(user_input)
            self._data[CONF_ENABLED_MODELS] = list(dict.fromkeys(self._storage_models))
            return await self.async_step_storage()

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULTS[CONF_NAME]): TextSelector(
                    TextSelectorConfig()
                ),
                vol.Required(CONF_PV_AC, default=DEFAULTS[CONF_PV_AC]): _entity(
                    "sensor"
                ),
                vol.Required(
                    CONF_MPPT_SENSORS, default=DEFAULTS[CONF_MPPT_SENSORS]
                ): _entity("sensor", multiple=True),
                vol.Required(
                    CONF_GRID_POWER, default=DEFAULTS[CONF_GRID_POWER]
                ): _entity("sensor"),
                vol.Required(
                    CONF_HOUSE_POWER, default=DEFAULTS[CONF_HOUSE_POWER]
                ): _entity("sensor"),
                vol.Required(
                    CONF_HOUSE_POWER_AVERAGE,
                    default=DEFAULTS[CONF_HOUSE_POWER_AVERAGE],
                ): _entity("sensor"),
                vol.Required(
                    CONF_PV_DAILY_ENERGY, default=DEFAULTS[CONF_PV_DAILY_ENERGY]
                ): _entity("sensor"),
                vol.Required(
                    CONF_FORECAST_SENSORS, default=DEFAULTS[CONF_FORECAST_SENSORS]
                ): _entity("sensor", multiple=True),
                vol.Optional(
                    CONF_MOBILE_NOTIFY_SERVICE,
                    default=DEFAULTS[CONF_MOBILE_NOTIFY_SERVICE],
                ): TextSelector(TextSelectorConfig()),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_storage(self, user_input: dict[str, Any] | None = None):
        """Configure Venus A or Venus E."""
        model = self._storage_models[self._storage_index]
        defaults = MODEL_DEFAULTS[model]
        current = (
            self._storage_defaults[self._storage_index]
            if self._storage_index < len(self._storage_defaults)
            and self._storage_defaults[self._storage_index].get("model") == model
            else {}
        )
        model_number = 1 + sum(
            item["model"] == model for item in self._storage_instances
        )
        errors = {}
        if user_input is not None and model == "A" and len(user_input.get("mppt_sensors", [])) > 4:
            errors["mppt_sensors"] = "too_many_mppts"
        elif user_input is not None:
            instance = dict(user_input)
            instance["model"] = model
            instance["id"] = str(
                current.get("id", f"venus_{model.lower()}_{model_number}")
            )
            instance["name"] = str(
                instance.pop("storage_name", f"Venus {model} {model_number}")
            )
            packs = instance.get("pack_soc")
            instance["modules"] = (
                max(1, min(6, len(packs)))
                if model == "A" and isinstance(packs, list)
                else 1
            )
            self._storage_instances.append(instance)
            self._storage_index += 1
            if self._storage_index < len(self._storage_models):
                return await self.async_step_storage()
            self._data[CONF_STORAGE_INSTANCES] = self._storage_instances
            if self._reconfigure_entry is not None:
                return self.async_update_reload_and_abort(
                    self._reconfigure_entry,
                    data_updates=self._data,
                )
            return self._async_create_config_entry()

        fields: dict[Any, Any] = {
            vol.Required(
                "storage_name",
                default=current.get("name", f"Venus {model} {model_number}"),
            ): TextSelector(TextSelectorConfig()),
            vol.Required("soc", default=current.get("soc", defaults["soc"])): _entity("sensor"),
            vol.Required("ac_power", default=current.get("ac_power", defaults["ac_power"])): _entity("sensor"),
            vol.Required("dc_power", default=current.get("dc_power", defaults["dc_power"])): _entity("sensor"),
            vol.Required("charge_limit", default=current.get("charge_limit", defaults["charge_limit"])): _entity("number"),
            vol.Required("discharge_limit", default=current.get("discharge_limit", defaults["discharge_limit"])): _entity("number"),
            vol.Required("auto_target", default=current.get("auto_target", defaults["auto_target"])): _entity("switch"),
            vol.Required("active", default=current.get("active", defaults["active"])): _entity("switch"),
            vol.Optional("charge_override"): _entity("input_boolean"),
            vol.Required("max_soc", default=current.get("max_soc", defaults["max_soc"])): _entity("number"),
            vol.Optional("min_soc", default=current.get("min_soc", defaults.get("min_soc"))): _entity("number"),
            vol.Required("max_cell_voltage", default=current.get("max_cell_voltage", defaults["max_cell_voltage"])): _entity("sensor"),
            vol.Required("max_cell_temp", default=current.get("max_cell_temp", defaults["max_cell_temp"])): _entity("sensor"),
            vol.Required("min_cell_temp", default=current.get("min_cell_temp", defaults["min_cell_temp"])): _entity("sensor"),
        }
        if model == "A":
            fields[vol.Required("pack_soc", default=current.get("pack_soc", defaults["pack_soc"]))] = _entity("sensor", multiple=True)
            fields[vol.Required("drift", default=current.get("drift", defaults["drift"]))] = _entity("sensor", multiple=True)
            fields[vol.Optional("mppt_sensors", default=current.get("mppt_sensors", []))] = _entity("sensor", multiple=True)
        else:
            fields[vol.Required("drift", default=current.get("drift", defaults["drift"]))] = _entity("sensor")
        return self.async_show_form(
            step_id="storage",
            description_placeholders={
                "storage": str(self._storage_index + 1),
                "model": model,
            },
            data_schema=vol.Schema(fields),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ):
        """Update the fixed Venus A and Venus E source mappings."""
        entry = self._get_reconfigure_entry()
        existing = storage_instances(dict(entry.data))
        self._reconfigure_entry = entry
        self._storage_models = ["A", "E"]
        self._storage_defaults = existing
        self._storage_instances = []
        self._storage_index = 0
        self._data = dict(entry.data)
        self._data[CONF_ENABLED_MODELS] = ["A", "E"]
        self._data.pop(CONF_STORAGE_INSTANCES, None)
        return await self.async_step_storage()

    def _async_create_config_entry(self):
        title = str(self._data.pop(CONF_NAME, DEFAULTS[CONF_NAME]))
        return self.async_create_entry(title=title, data=self._data)


class SpeicherLadelogikOptionsFlow(config_entries.OptionsFlow):
    """Change optional runtime settings without reinstalling the integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        current = self._config_entry.options.get(
            CONF_MOBILE_NOTIFY_SERVICE,
            self._config_entry.data.get(CONF_MOBILE_NOTIFY_SERVICE, ""),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_MOBILE_NOTIFY_SERVICE,
                        default=current,
                    ): TextSelector(TextSelectorConfig()),
                }
            ),
        )
