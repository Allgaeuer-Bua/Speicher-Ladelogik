"""Config flow for Speicher-Ladelogik."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
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
    CONF_A_DISCHARGE_LIMIT,
    CONF_A_MAX_CELL_TEMP,
    CONF_A_MAX_CELL_VOLTAGE,
    CONF_A_MAX_SOC,
    CONF_A_MIN_CELL_TEMP,
    CONF_A_PACK_DRIFT,
    CONF_A_PACK_SOC,
    CONF_A_SOC,
    CONF_A_USABLE_CAPACITY,
    CONF_E_AC_POWER,
    CONF_E_ACTIVE,
    CONF_E_AUTO_TARGET,
    CONF_E_CELL_DRIFT,
    CONF_E_CHARGE_LIMIT,
    CONF_E_CHARGE_OVERRIDE,
    CONF_E_DISCHARGE_LIMIT,
    CONF_E_MAX_CELL_TEMP,
    CONF_E_MAX_CELL_VOLTAGE,
    CONF_E_MAX_SOC,
    CONF_E_MIN_CELL_TEMP,
    CONF_E_SOC,
    CONF_E_USABLE_CAPACITY,
    CONF_FORECAST_SENSORS,
    CONF_GRID_POWER,
    CONF_HOUSE_POWER,
    CONF_HOUSE_POWER_AVERAGE,
    CONF_MPPT_SENSORS,
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

    VERSION = 1
    MINOR_VERSION = 0

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Configure common sources."""
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            self._data.update(user_input)
            return await self.async_step_venus_a()

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
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_venus_a(self, user_input: dict[str, Any] | None = None):
        """Configure Venus A sources and actuators."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_venus_e()

        schema = vol.Schema(
            {
                vol.Required(CONF_A_SOC, default=DEFAULTS[CONF_A_SOC]): _entity("sensor"),
                vol.Required(
                    CONF_A_AC_POWER, default=DEFAULTS[CONF_A_AC_POWER]
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
                vol.Required(
                    CONF_A_USABLE_CAPACITY, default=DEFAULTS[CONF_A_USABLE_CAPACITY]
                ): _entity(["number", "input_number"]),
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
            }
        )
        return self.async_show_form(step_id="venus_a", data_schema=schema)

    async def async_step_venus_e(self, user_input: dict[str, Any] | None = None):
        """Configure Venus E sources and actuators."""
        if user_input is not None:
            self._data.update(user_input)
            title = str(self._data.pop(CONF_NAME, DEFAULTS[CONF_NAME]))
            return self.async_create_entry(title=title, data=self._data)

        schema = vol.Schema(
            {
                vol.Required(CONF_E_SOC, default=DEFAULTS[CONF_E_SOC]): _entity("sensor"),
                vol.Required(
                    CONF_E_AC_POWER, default=DEFAULTS[CONF_E_AC_POWER]
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
                vol.Required(
                    CONF_E_USABLE_CAPACITY, default=DEFAULTS[CONF_E_USABLE_CAPACITY]
                ): _entity(["number", "input_number"]),
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
