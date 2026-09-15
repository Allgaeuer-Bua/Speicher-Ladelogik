"""Constants for Speicher-Ladelogik."""

from __future__ import annotations

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "speicher_ladelogik"
NAME: Final = "Speicher-Ladelogik"
VERSION: Final = "1.0.0-beta.4"

PLATFORMS: Final = [Platform.SENSOR]
UPDATE_INTERVAL_SECONDS: Final = 30

SHADOW_TRACKED_ENTITIES: Final = (
    "sun.sun",
    "sensor.speicher_ladelogik_planung",
    "sensor.speicher_ladelogik_kalibrierung_planung",
    "sensor.speicher_ladelogik_lernspeicher",
    "input_boolean.speicher_ladelogik_aktiv",
    "input_boolean.speicher_ladelogik_mittagsspitzen",
    "input_boolean.speicher_ladelogik_manuell_a_aktiv",
    "input_boolean.speicher_ladelogik_manuell_e_aktiv",
    "input_boolean.speicher_ladelogik_kalibrierung_a_freigegeben",
    "input_boolean.speicher_ladelogik_kalibrierung_e_freigegeben",
    "input_boolean.speicher_ladelogik_kalibrierung_a_laden_sperren",
    "input_boolean.speicher_ladelogik_kalibrierung_e_laden_sperren",
    "input_boolean.speicher_ladelogik_v1_beta_1_initialisiert",
    "input_select.speicher_ladelogik_betriebsart",
    "input_text.speicher_ladelogik_kalibrierung_sitzung",
    "input_text.speicher_ladelogik_kalibrierung_vormerkungen",
    "input_text.speicher_ladelogik_sicherung",
    "input_text.speicher_ladelogik_kalibrierung_sicherung",
    "input_number.speicher_ladelogik_ziel_soc",
    "input_number.speicher_ladelogik_mindestreserve",
    "input_number.speicher_ladelogik_prognose_sicherheit",
    "input_number.speicher_ladelogik_unplanbare_reserve",
    "input_number.speicher_ladelogik_ladewirkungsgrad",
    "input_number.speicher_ladelogik_hysterese",
    "input_number.speicher_ladelogik_schwacher_tag",
    "input_number.speicher_ladelogik_mittlerer_tag",
    "input_number.speicher_ladelogik_starker_tag",
    "input_number.speicher_ladelogik_knappheitsreserve",
    "input_number.speicher_ladelogik_min_effiziente_leistung",
    "input_number.speicher_ladelogik_venus_a_packs",
    "input_number.speicher_ladelogik_schreibfehler",
    "input_number.speicher_ladelogik_schreibfehler_a",
    "input_number.speicher_ladelogik_schreibfehler_e",
    "input_number.speicher_ladelogik_manuell_laden_a_w",
    "input_number.speicher_ladelogik_manuell_entladen_a_w",
    "input_number.speicher_ladelogik_manuell_laden_e_w",
    "input_number.speicher_ladelogik_manuell_entladen_e_w",
)

CONF_NAME: Final = "name"
CONF_PV_AC: Final = "pv_ac"
CONF_MPPT_SENSORS: Final = "mppt_sensors"
CONF_GRID_POWER: Final = "grid_power"
CONF_HOUSE_POWER: Final = "house_power"
CONF_HOUSE_POWER_AVERAGE: Final = "house_power_average"
CONF_PV_DAILY_ENERGY: Final = "pv_daily_energy"
CONF_FORECAST_SENSORS: Final = "forecast_sensors"

CONF_A_SOC: Final = "a_soc"
CONF_A_AC_POWER: Final = "a_ac_power"
CONF_A_CHARGE_LIMIT: Final = "a_charge_limit"
CONF_A_DISCHARGE_LIMIT: Final = "a_discharge_limit"
CONF_A_AUTO_TARGET: Final = "a_auto_target"
CONF_A_ACTIVE: Final = "a_active"
CONF_A_CHARGE_OVERRIDE: Final = "a_charge_override"
CONF_A_MAX_SOC: Final = "a_max_soc"
CONF_A_USABLE_CAPACITY: Final = "a_usable_capacity"
CONF_A_PACK_SOC: Final = "a_pack_soc"
CONF_A_MAX_CELL_VOLTAGE: Final = "a_max_cell_voltage"
CONF_A_MAX_CELL_TEMP: Final = "a_max_cell_temp"
CONF_A_MIN_CELL_TEMP: Final = "a_min_cell_temp"
CONF_A_PACK_DRIFT: Final = "a_pack_drift"

CONF_E_SOC: Final = "e_soc"
CONF_E_AC_POWER: Final = "e_ac_power"
CONF_E_CHARGE_LIMIT: Final = "e_charge_limit"
CONF_E_DISCHARGE_LIMIT: Final = "e_discharge_limit"
CONF_E_AUTO_TARGET: Final = "e_auto_target"
CONF_E_ACTIVE: Final = "e_active"
CONF_E_CHARGE_OVERRIDE: Final = "e_charge_override"
CONF_E_MAX_SOC: Final = "e_max_soc"
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
    CONF_A_SOC: "sensor.marstek_venus_a_soc_batterie",
    CONF_A_AC_POWER: "sensor.marstek_venus_a_ac_leistung",
    CONF_A_CHARGE_LIMIT: "number.marstek_venus_a_maximale_ladeleistung",
    CONF_A_DISCHARGE_LIMIT: "number.marstek_venus_a_maximale_entladeleistung",
    CONF_A_AUTO_TARGET: "switch.astrameter_venus_a_auto_target",
    CONF_A_ACTIVE: "switch.astrameter_venus_a_active",
    CONF_A_MAX_SOC: "number.marstek_venus_a_maximaler_soc",
    CONF_A_USABLE_CAPACITY: "input_number.venus_a_verfugbare_kapazitat",
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
    CONF_E_SOC: "sensor.marstek_venus_e_soc",
    CONF_E_AC_POWER: "sensor.marstek_venus_e_ac_leistung",
    CONF_E_CHARGE_LIMIT: "number.marstek_venus_e_ladeleistung",
    CONF_E_DISCHARGE_LIMIT: "number.marstek_venus_e_entladeleistung",
    CONF_E_AUTO_TARGET: "switch.astrameter_venus_e_auto_target",
    CONF_E_ACTIVE: "switch.astrameter_venus_e_active",
    CONF_E_MAX_SOC: "number.marstek_venus_e_obere_ladegrenze_kapazitat",
    CONF_E_USABLE_CAPACITY: "input_number.venus_e_verfugbare_kapazitat",
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
    CONF_A_CHARGE_LIMIT,
    CONF_A_DISCHARGE_LIMIT,
    CONF_A_AUTO_TARGET,
    CONF_A_ACTIVE,
    CONF_A_CHARGE_OVERRIDE,
    CONF_A_MAX_SOC,
    CONF_A_USABLE_CAPACITY,
    CONF_A_PACK_SOC,
    CONF_A_MAX_CELL_VOLTAGE,
    CONF_A_MAX_CELL_TEMP,
    CONF_A_MIN_CELL_TEMP,
    CONF_A_PACK_DRIFT,
)

VENUS_E_KEYS: Final = (
    CONF_E_SOC,
    CONF_E_AC_POWER,
    CONF_E_CHARGE_LIMIT,
    CONF_E_DISCHARGE_LIMIT,
    CONF_E_AUTO_TARGET,
    CONF_E_ACTIVE,
    CONF_E_CHARGE_OVERRIDE,
    CONF_E_MAX_SOC,
    CONF_E_USABLE_CAPACITY,
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
