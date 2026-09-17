"""Config flow for Speicher-Ladelogik."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from .const import (
    CONF_A_AC_POWER,
    CONF_A_DC_POWER,
    CONF_A_ACTIVE,
    CONF_A_AUTO_TARGET,
    CONF_A_CHARGE_LIMIT,
    CONF_A_CHARGE_OVERRIDE,
    CONF_A_DISCHARGE_LIMIT,
    CONF_A_MAX_CELL_TEMP,
    CONF_A_MAX_CELL_VOLTAGE,
    CONF_A_MAX_SOC,
    CONF_A_MIN_SOC,
    CONF_A_MIN_CELL_TEMP,
    CONF_A_PACK_DRIFT,
    CONF_A_PACK_SOC,
    CONF_A_MPPT_SENSORS,
    CONF_A_SOC,
    CONF_D_AC_POWER,
    CONF_D_ACTIVE,
    CONF_D_AUTO_TARGET,
    CONF_D_CHARGE_LIMIT,
    CONF_D_CHARGE_OVERRIDE,
    CONF_D_DC_POWER,
    CONF_D_DISCHARGE_LIMIT,
    CONF_D_MAX_CELL_TEMP,
    CONF_D_MAX_CELL_VOLTAGE,
    CONF_D_MAX_SOC,
    CONF_D_MIN_CELL_TEMP,
    CONF_D_MIN_SOC,
    CONF_D_MPPT_SENSORS,
    CONF_D_PACK_DRIFT,
    CONF_D_PACK_SOC,
    CONF_D_SOC,
    CONF_ENABLED_MODELS,
    CONF_E_AC_POWER,
    CONF_E_DC_POWER,
    CONF_E_ACTIVE,
    CONF_E_AUTO_TARGET,
    CONF_E_CELL_DRIFT,
    CONF_E_CHARGE_LIMIT,
    CONF_E_CHARGE_OVERRIDE,
    CONF_E_DISCHARGE_LIMIT,
    CONF_E_MAX_CELL_TEMP,
    CONF_E_MAX_CELL_VOLTAGE,
    CONF_E_MAX_SOC,
    CONF_E_MIN_SOC,
    CONF_E_MIN_CELL_TEMP,
    CONF_E_SOC,
    CONF_FORECAST_SENSORS,
    CONF_GRID_POWER,
    CONF_HOUSE_POWER,
    CONF_HOUSE_POWER_AVERAGE,
    CONF_MPPT_SENSORS,
    CONF_MOBILE_NOTIFY_SERVICE,
    CONF_NAME,
    CONF_PV_AC,
    CONF_PV_DAILY_ENERGY,
    DEFAULTS,
    DOMAIN,
)


def _entity(domain: str | list[str], *, multiple: bool = False) -> EntitySelector:
    return EntitySelector(EntitySelectorConfig(domain=domain, multiple=multiple))


class SpeicherLadelogikConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure Speicher-Ladelogik from the UI."""

    VERSION = 2
    MINOR_VERSION = 0

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

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
            self._data.update(user_input)
            return await self._async_next_storage("A")

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULTS[CONF_NAME]): TextSelector(
                    TextSelectorConfig()
                ),
                vol.Required(
                    CONF_ENABLED_MODELS,
                    default=DEFAULTS[CONF_ENABLED_MODELS],
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=["A", "D", "E"],
                        multiple=True,
                        mode=SelectSelectorMode.LIST,
                    )
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

    async def async_step_venus_a(self, user_input: dict[str, Any] | None = None):
        """Configure Venus A sources and actuators."""
        if user_input is not None:
            self._data.update(user_input)
            return await self._async_next_storage("D")

        schema = vol.Schema(
            {
                vol.Required(CONF_A_SOC, default=DEFAULTS[CONF_A_SOC]): _entity("sensor"),
                vol.Required(
                    CONF_A_AC_POWER, default=DEFAULTS[CONF_A_AC_POWER]
                ): _entity("sensor"),
                vol.Required(
                    CONF_A_DC_POWER, default=DEFAULTS[CONF_A_DC_POWER]
                ): _entity("sensor"),
                vol.Required(
                    CONF_A_CHARGE_LIMIT, default=DEFAULTS[CONF_A_CHARGE_LIMIT]
                ): _entity("number"),
                vol.Required(
                    CONF_A_DISCHARGE_LIMIT, default=DEFAULTS[CONF_A_DISCHARGE_LIMIT]
                ): _entity("number"),
                vol.Required(
                    CONF_A_AUTO_TARGET, default=DEFAULTS[CONF_A_AUTO_TARGET]
                ): _entity("switch"),
                vol.Required(CONF_A_ACTIVE, default=DEFAULTS[CONF_A_ACTIVE]): _entity(
                    "switch"
                ),
                vol.Optional(CONF_A_CHARGE_OVERRIDE): _entity("input_boolean"),
                vol.Required(CONF_A_MAX_SOC, default=DEFAULTS[CONF_A_MAX_SOC]): _entity(
                    "number"
                ),
                vol.Optional(CONF_A_MIN_SOC): _entity("number"),
                vol.Required(
                    CONF_A_PACK_SOC, default=DEFAULTS[CONF_A_PACK_SOC]
                ): _entity("sensor", multiple=True),
                vol.Required(
                    CONF_A_MAX_CELL_VOLTAGE,
                    default=DEFAULTS[CONF_A_MAX_CELL_VOLTAGE],
                ): _entity("sensor"),
                vol.Required(
                    CONF_A_MAX_CELL_TEMP, default=DEFAULTS[CONF_A_MAX_CELL_TEMP]
                ): _entity("sensor"),
                vol.Required(
                    CONF_A_MIN_CELL_TEMP, default=DEFAULTS[CONF_A_MIN_CELL_TEMP]
                ): _entity("sensor"),
                vol.Required(
                    CONF_A_PACK_DRIFT, default=DEFAULTS[CONF_A_PACK_DRIFT]
                ): _entity("sensor", multiple=True),
                vol.Optional(CONF_A_MPPT_SENSORS, default=[]): _entity(
                    "sensor", multiple=True
                ),
            }
        )
        return self.async_show_form(step_id="venus_a", data_schema=schema)

    async def async_step_venus_d(self, user_input: dict[str, Any] | None = None):
        """Configure Venus D sources and actuators."""
        if user_input is not None:
            self._data.update(user_input)
            return await self._async_next_storage("E")

        schema = vol.Schema(
            {
                vol.Required(CONF_D_SOC): _entity("sensor"),
                vol.Required(CONF_D_AC_POWER): _entity("sensor"),
                vol.Required(CONF_D_DC_POWER): _entity("sensor"),
                vol.Required(CONF_D_CHARGE_LIMIT): _entity("number"),
                vol.Required(CONF_D_DISCHARGE_LIMIT): _entity("number"),
                vol.Required(CONF_D_AUTO_TARGET): _entity("switch"),
                vol.Required(CONF_D_ACTIVE): _entity("switch"),
                vol.Optional(CONF_D_CHARGE_OVERRIDE): _entity("input_boolean"),
                vol.Required(CONF_D_MAX_SOC): _entity("number"),
                vol.Optional(CONF_D_MIN_SOC): _entity("number"),
                vol.Required(CONF_D_PACK_SOC): _entity("sensor", multiple=True),
                vol.Required(CONF_D_MAX_CELL_VOLTAGE): _entity("sensor"),
                vol.Required(CONF_D_MAX_CELL_TEMP): _entity("sensor"),
                vol.Required(CONF_D_MIN_CELL_TEMP): _entity("sensor"),
                vol.Required(CONF_D_PACK_DRIFT): _entity("sensor", multiple=True),
                vol.Optional(CONF_D_MPPT_SENSORS, default=[]): _entity(
                    "sensor", multiple=True
                ),
            }
        )
        return self.async_show_form(step_id="venus_d", data_schema=schema)

    async def async_step_venus_e(self, user_input: dict[str, Any] | None = None):
        """Configure Venus E sources and actuators."""
        if user_input is not None:
            self._data.update(user_input)
            return self._async_create_config_entry()

        schema = vol.Schema(
            {
                vol.Required(CONF_E_SOC, default=DEFAULTS[CONF_E_SOC]): _entity("sensor"),
                vol.Required(
                    CONF_E_AC_POWER, default=DEFAULTS[CONF_E_AC_POWER]
                ): _entity("sensor"),
                vol.Required(
                    CONF_E_DC_POWER, default=DEFAULTS[CONF_E_DC_POWER]
                ): _entity("sensor"),
                vol.Required(
                    CONF_E_CHARGE_LIMIT, default=DEFAULTS[CONF_E_CHARGE_LIMIT]
                ): _entity("number"),
                vol.Required(
                    CONF_E_DISCHARGE_LIMIT, default=DEFAULTS[CONF_E_DISCHARGE_LIMIT]
                ): _entity("number"),
                vol.Required(
                    CONF_E_AUTO_TARGET, default=DEFAULTS[CONF_E_AUTO_TARGET]
                ): _entity("switch"),
                vol.Required(CONF_E_ACTIVE, default=DEFAULTS[CONF_E_ACTIVE]): _entity(
                    "switch"
                ),
                vol.Optional(CONF_E_CHARGE_OVERRIDE): _entity("input_boolean"),
                vol.Required(CONF_E_MAX_SOC, default=DEFAULTS[CONF_E_MAX_SOC]): _entity(
                    "number"
                ),
                vol.Required(CONF_E_MIN_SOC, default=DEFAULTS[CONF_E_MIN_SOC]): _entity(
                    "number"
                ),
                vol.Required(
                    CONF_E_MAX_CELL_VOLTAGE,
                    default=DEFAULTS[CONF_E_MAX_CELL_VOLTAGE],
                ): _entity("sensor"),
                vol.Required(
                    CONF_E_MAX_CELL_TEMP, default=DEFAULTS[CONF_E_MAX_CELL_TEMP]
                ): _entity("sensor"),
                vol.Required(
                    CONF_E_MIN_CELL_TEMP, default=DEFAULTS[CONF_E_MIN_CELL_TEMP]
                ): _entity("sensor"),
                vol.Required(
                    CONF_E_CELL_DRIFT, default=DEFAULTS[CONF_E_CELL_DRIFT]
                ): _entity("sensor"),
            }
        )
        return self.async_show_form(step_id="venus_e", data_schema=schema)

    async def _async_next_storage(self, model: str):
        enabled = self._data.get(CONF_ENABLED_MODELS, DEFAULTS[CONF_ENABLED_MODELS])
        order = ["A", "D", "E"]
        for candidate in order[order.index(model):]:
            if candidate in enabled:
                return await getattr(
                    self, f"async_step_venus_{candidate.lower()}"
                )()
        return self._async_create_config_entry()

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
