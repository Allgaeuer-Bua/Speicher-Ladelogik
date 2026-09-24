"""Constants for Speicher-Ladelogik."""

from __future__ import annotations

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "speicher_ladelogik"
NAME: Final = "Speicher-Ladelogik"
VERSION: Final = "1.1.1-beta.3"

PLATFORMS: Final = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.BUTTON,
]
UPDATE_INTERVAL_SECONDS: Final = 15

CONF_NAME: Final = "name"
CONF_PV_AC: Final = "pv_ac"
CONF_MPPT_SENSORS: Final = "mppt_sensors"
CONF_GRID_POWER: Final = "grid_power"
CONF_HOUSE_POWER: Final = "house_power"
CONF_HOUSE_POWER_AVERAGE: Final = "house_power_average"
CONF_PV_DAILY_ENERGY: Final = "pv_daily_energy"
CONF_FORECAST_SENSORS: Final = "forecast_sensors"
CONF_MOBILE_NOTIFY_SERVICE: Final = "mobile_notify_service"
CONF_ENABLED_MODELS: Final = "enabled_models"
CONF_STORAGE_INSTANCES: Final = "storage_instances"

CONF_A_SOC: Final = "a_soc"
CONF_A_AC_POWER: Final = "a_ac_power"
CONF_A_DC_POWER: Final = "a_dc_power"
CONF_A_CHARGE_LIMIT: Final = "a_charge_limit"
CONF_A_DISCHARGE_LIMIT: Final = "a_discharge_limit"
CONF_A_AUTO_TARGET: Final = "a_auto_target"
CONF_A_ACTIVE: Final = "a_active"
CONF_A_CHARGE_OVERRIDE: Final = "a_charge_override"
CONF_A_MAX_SOC: Final = "a_max_soc"
CONF_A_MIN_SOC: Final = "a_min_soc"
CONF_A_USABLE_CAPACITY: Final = "a_usable_capacity"
CONF_A_PACK_SOC: Final = "a_pack_soc"
CONF_A_MAX_CELL_VOLTAGE: Final = "a_max_cell_voltage"
CONF_A_MAX_CELL_TEMP: Final = "a_max_cell_temp"
CONF_A_MIN_CELL_TEMP: Final = "a_min_cell_temp"
CONF_A_PACK_DRIFT: Final = "a_pack_drift"
CONF_A_MPPT_SENSORS: Final = "a_mppt_sensors"

CONF_D_SOC: Final = "d_soc"
CONF_D_AC_POWER: Final = "d_ac_power"
CONF_D_DC_POWER: Final = "d_dc_power"
CONF_D_CHARGE_LIMIT: Final = "d_charge_limit"
CONF_D_DISCHARGE_LIMIT: Final = "d_discharge_limit"
CONF_D_AUTO_TARGET: Final = "d_auto_target"
CONF_D_ACTIVE: Final = "d_active"
CONF_D_CHARGE_OVERRIDE: Final = "d_charge_override"
CONF_D_MAX_SOC: Final = "d_max_soc"
CONF_D_MIN_SOC: Final = "d_min_soc"
CONF_D_PACK_SOC: Final = "d_pack_soc"
CONF_D_MAX_CELL_VOLTAGE: Final = "d_max_cell_voltage"
CONF_D_MAX_CELL_TEMP: Final = "d_max_cell_temp"
CONF_D_MIN_CELL_TEMP: Final = "d_min_cell_temp"
CONF_D_PACK_DRIFT: Final = "d_pack_drift"
CONF_D_MPPT_SENSORS: Final = "d_mppt_sensors"

CONF_E_SOC: Final = "e_soc"
CONF_E_AC_POWER: Final = "e_ac_power"
CONF_E_DC_POWER: Final = "e_dc_power"
CONF_E_CHARGE_LIMIT: Final = "e_charge_limit"
CONF_E_DISCHARGE_LIMIT: Final = "e_discharge_limit"
CONF_E_AUTO_TARGET: Final = "e_auto_target"
CONF_E_ACTIVE: Final = "e_active"
CONF_E_CHARGE_OVERRIDE: Final = "e_charge_override"
CONF_E_MAX_SOC: Final = "e_max_soc"
CONF_E_MIN_SOC: Final = "e_min_soc"
CONF_E_USABLE_CAPACITY: Final = "e_usable_capacity"
CONF_E_MAX_CELL_VOLTAGE: Final = "e_max_cell_voltage"
CONF_E_MAX_CELL_TEMP: Final = "e_max_cell_temp"
CONF_E_MIN_CELL_TEMP: Final = "e_min_cell_temp"
CONF_E_CELL_DRIFT: Final = "e_cell_drift"

DEFAULTS: Final = {
    CONF_NAME: NAME,
    CONF_PV_AC: "sensor.aktuelle_pv_leistung",
    CONF_MPPT_SENSORS: [
        "sensor.sg10rt_mppt1_leistung",
        "sensor.sg10rt_mppt2_leistung",
        "sensor.sg12rt_mppt1_leistung",
        "sensor.sg12rt_mppt2_leistung",
    ],
    CONF_GRID_POWER: "sensor.stromzahler_leistung",
    CONF_HOUSE_POWER: "sensor.hausleistung_gesamt",
    CONF_HOUSE_POWER_AVERAGE: "sensor.hausleistung_gesamt_30_min",
    CONF_PV_DAILY_ENERGY: "sensor.pv_produktion_tag",
    CONF_FORECAST_SENSORS: [
        "sensor.sw_energy_production_today",
        "sensor.so_energy_production_today",
        "sensor.no_energy_production_today",
        "sensor.sw_energy_production_tomorrow",
        "sensor.so_energy_production_tomorrow",
        "sensor.no_energy_production_tomorrow",
    ],
    CONF_MOBILE_NOTIFY_SERVICE: "",
    CONF_ENABLED_MODELS: ["A", "E"],
    CONF_A_SOC: "sensor.marstek_venus_a_soc_batterie",
    CONF_A_AC_POWER: "sensor.marstek_venus_a_ac_leistung",
    CONF_A_DC_POWER: "sensor.marstek_venus_a_batterieleistung",
    CONF_A_CHARGE_LIMIT: "number.marstek_venus_a_maximale_ladeleistung",
    CONF_A_DISCHARGE_LIMIT: "number.marstek_venus_a_maximale_entladeleistung",
    CONF_A_AUTO_TARGET: "switch.astrameter_venus_a_auto_target",
    CONF_A_ACTIVE: "switch.astrameter_venus_a_active",
    CONF_A_MAX_SOC: "number.marstek_venus_a_maximaler_soc",
    CONF_A_MIN_SOC: "number.marstek_venus_a_minimaler_soc",
    CONF_A_PACK_SOC: [
        "sensor.marstek_venus_a_soc_batteriepack_1",
        "sensor.marstek_venus_a_soc_batteriepack_2",
    ],
    CONF_A_MAX_CELL_VOLTAGE: "sensor.marstek_venus_a_maximale_zellenspannung",
    CONF_A_MAX_CELL_TEMP: "sensor.marstek_venus_a_maximale_zellentemperatur",
    CONF_A_MIN_CELL_TEMP: "sensor.marstek_venus_a_minimale_zellentemperatur",
    CONF_A_PACK_DRIFT: [
        "sensor.venus_a_pack_1_zelldrift",
        "sensor.venus_a_pack_2_zelldrift",
    ],
    CONF_A_MPPT_SENSORS: [],
    CONF_D_SOC: "sensor.marstek_venus_d_soc",
    CONF_D_AC_POWER: "sensor.marstek_venus_d_ac_leistung",
    CONF_D_DC_POWER: "sensor.marstek_venus_d_batterieleistung",
    CONF_D_CHARGE_LIMIT: "number.marstek_venus_d_maximale_ladeleistung",
    CONF_D_DISCHARGE_LIMIT: "number.marstek_venus_d_maximale_entladeleistung",
    CONF_D_AUTO_TARGET: "switch.astrameter_venus_d_auto_target",
    CONF_D_ACTIVE: "switch.astrameter_venus_d_active",
    CONF_D_MAX_SOC: "number.marstek_venus_d_maximaler_soc",
    CONF_D_MIN_SOC: "number.marstek_venus_d_minimaler_soc",
    CONF_D_PACK_SOC: [
        "sensor.marstek_venus_d_soc_batteriepack_1",
        "sensor.marstek_venus_d_soc_batteriepack_2",
    ],
    CONF_D_MAX_CELL_VOLTAGE: "sensor.marstek_venus_d_maximale_zellenspannung",
    CONF_D_MAX_CELL_TEMP: "sensor.marstek_venus_d_maximale_zellentemperatur",
    CONF_D_MIN_CELL_TEMP: "sensor.marstek_venus_d_minimale_zellentemperatur",
    CONF_D_PACK_DRIFT: [
        "sensor.venus_d_pack_1_zelldrift",
        "sensor.venus_d_pack_2_zelldrift",
    ],
    CONF_D_MPPT_SENSORS: [],
    CONF_E_SOC: "sensor.marstek_venus_e_soc",
    CONF_E_AC_POWER: "sensor.marstek_venus_e_ac_leistung",
    CONF_E_DC_POWER: "sensor.marstek_venus_e_dc_leistung",
    CONF_E_CHARGE_LIMIT: "number.marstek_venus_e_ladeleistung",
    CONF_E_DISCHARGE_LIMIT: "number.marstek_venus_e_entladeleistung",
    CONF_E_AUTO_TARGET: "switch.astrameter_venus_e_auto_target",
    CONF_E_ACTIVE: "switch.astrameter_venus_e_active",
    CONF_E_MAX_SOC: "number.marstek_venus_e_obere_ladegrenze_kapazitat",
    CONF_E_MIN_SOC: "number.marstek_venus_e_untere_ladegrenze_kapazitat",
    CONF_E_MAX_CELL_VOLTAGE: "sensor.marstek_venus_e_max_zellspannung",
    CONF_E_MAX_CELL_TEMP: "sensor.marstek_venus_e_max_zelltemperatur",
    CONF_E_MIN_CELL_TEMP: "sensor.marstek_venus_e_min_zelltemperatur",
    CONF_E_CELL_DRIFT: "sensor.marstek_venus_e_zellspannungs_differenz",
}

COMMON_KEYS: Final = (
    CONF_PV_AC,
    CONF_MPPT_SENSORS,
    CONF_GRID_POWER,
    CONF_HOUSE_POWER,
    CONF_HOUSE_POWER_AVERAGE,
    CONF_PV_DAILY_ENERGY,
    CONF_FORECAST_SENSORS,
)

VENUS_A_KEYS: Final = (
    CONF_A_SOC,
    CONF_A_AC_POWER,
    CONF_A_DC_POWER,
    CONF_A_CHARGE_LIMIT,
    CONF_A_DISCHARGE_LIMIT,
    CONF_A_AUTO_TARGET,
    CONF_A_ACTIVE,
    CONF_A_CHARGE_OVERRIDE,
    CONF_A_MAX_SOC,
    CONF_A_MIN_SOC,
    CONF_A_PACK_SOC,
    CONF_A_MAX_CELL_VOLTAGE,
    CONF_A_MAX_CELL_TEMP,
    CONF_A_MIN_CELL_TEMP,
    CONF_A_PACK_DRIFT,
    CONF_A_MPPT_SENSORS,
)

VENUS_D_KEYS: Final = (
    CONF_D_SOC,
    CONF_D_AC_POWER,
    CONF_D_DC_POWER,
    CONF_D_CHARGE_LIMIT,
    CONF_D_DISCHARGE_LIMIT,
    CONF_D_AUTO_TARGET,
    CONF_D_ACTIVE,
    CONF_D_CHARGE_OVERRIDE,
    CONF_D_MAX_SOC,
    CONF_D_MIN_SOC,
    CONF_D_PACK_SOC,
    CONF_D_MAX_CELL_VOLTAGE,
    CONF_D_MAX_CELL_TEMP,
    CONF_D_MIN_CELL_TEMP,
    CONF_D_PACK_DRIFT,
    CONF_D_MPPT_SENSORS,
)

VENUS_E_KEYS: Final = (
    CONF_E_SOC,
    CONF_E_AC_POWER,
    CONF_E_DC_POWER,
    CONF_E_CHARGE_LIMIT,
    CONF_E_DISCHARGE_LIMIT,
    CONF_E_AUTO_TARGET,
    CONF_E_ACTIVE,
    CONF_E_CHARGE_OVERRIDE,
    CONF_E_MAX_SOC,
    CONF_E_MIN_SOC,
    CONF_E_MAX_CELL_VOLTAGE,
    CONF_E_MAX_CELL_TEMP,
    CONF_E_MIN_CELL_TEMP,
    CONF_E_CELL_DRIFT,
)

REQUIRED_COMMON_KEYS: Final = (
    CONF_GRID_POWER,
    CONF_HOUSE_POWER,
    CONF_PV_DAILY_ENERGY,
)

REQUIRED_A_KEYS: Final = (
    CONF_A_SOC,
    CONF_A_AC_POWER,
    CONF_A_CHARGE_LIMIT,
    CONF_A_DISCHARGE_LIMIT,
    CONF_A_AUTO_TARGET,
    CONF_A_ACTIVE,
)

REQUIRED_E_KEYS: Final = (
    CONF_E_SOC,
    CONF_E_AC_POWER,
    CONF_E_CHARGE_LIMIT,
    CONF_E_DISCHARGE_LIMIT,
    CONF_E_AUTO_TARGET,
    CONF_E_ACTIVE,
)

REQUIRED_D_KEYS: Final = (
    CONF_D_SOC,
    CONF_D_AC_POWER,
    CONF_D_CHARGE_LIMIT,
    CONF_D_DISCHARGE_LIMIT,
    CONF_D_AUTO_TARGET,
    CONF_D_ACTIVE,
)
