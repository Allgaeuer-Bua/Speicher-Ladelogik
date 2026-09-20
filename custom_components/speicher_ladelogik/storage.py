"""Storage-instance configuration and V1.0 compatibility helpers."""

from __future__ import annotations

from typing import Any

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
    CONF_STORAGE_INSTANCES,
    DEFAULTS,
)

SLOT_KEYS = ("A", "D", "E")

SLOT_FIELDS: dict[str, dict[str, str]] = {
    "A": {
        "soc": CONF_A_SOC,
        "ac_power": CONF_A_AC_POWER,
        "dc_power": CONF_A_DC_POWER,
        "charge_limit": CONF_A_CHARGE_LIMIT,
        "discharge_limit": CONF_A_DISCHARGE_LIMIT,
        "auto_target": CONF_A_AUTO_TARGET,
        "active": CONF_A_ACTIVE,
        "charge_override": CONF_A_CHARGE_OVERRIDE,
        "max_soc": CONF_A_MAX_SOC,
        "min_soc": CONF_A_MIN_SOC,
        "pack_soc": CONF_A_PACK_SOC,
        "max_cell_voltage": CONF_A_MAX_CELL_VOLTAGE,
        "max_cell_temp": CONF_A_MAX_CELL_TEMP,
        "min_cell_temp": CONF_A_MIN_CELL_TEMP,
        "drift": CONF_A_PACK_DRIFT,
        "mppt_sensors": CONF_A_MPPT_SENSORS,
    },
    "D": {
        "soc": CONF_D_SOC,
        "ac_power": CONF_D_AC_POWER,
        "dc_power": CONF_D_DC_POWER,
        "charge_limit": CONF_D_CHARGE_LIMIT,
        "discharge_limit": CONF_D_DISCHARGE_LIMIT,
        "auto_target": CONF_D_AUTO_TARGET,
        "active": CONF_D_ACTIVE,
        "charge_override": CONF_D_CHARGE_OVERRIDE,
        "max_soc": CONF_D_MAX_SOC,
        "min_soc": CONF_D_MIN_SOC,
        "pack_soc": CONF_D_PACK_SOC,
        "max_cell_voltage": CONF_D_MAX_CELL_VOLTAGE,
        "max_cell_temp": CONF_D_MAX_CELL_TEMP,
        "min_cell_temp": CONF_D_MIN_CELL_TEMP,
        "drift": CONF_D_PACK_DRIFT,
        "mppt_sensors": CONF_D_MPPT_SENSORS,
    },
    "E": {
        "soc": CONF_E_SOC,
        "ac_power": CONF_E_AC_POWER,
        "dc_power": CONF_E_DC_POWER,
        "charge_limit": CONF_E_CHARGE_LIMIT,
        "discharge_limit": CONF_E_DISCHARGE_LIMIT,
        "auto_target": CONF_E_AUTO_TARGET,
        "active": CONF_E_ACTIVE,
        "charge_override": CONF_E_CHARGE_OVERRIDE,
        "max_soc": CONF_E_MAX_SOC,
        "min_soc": CONF_E_MIN_SOC,
        "max_cell_voltage": CONF_E_MAX_CELL_VOLTAGE,
        "max_cell_temp": CONF_E_MAX_CELL_TEMP,
        "min_cell_temp": CONF_E_MIN_CELL_TEMP,
        "drift": CONF_E_CELL_DRIFT,
        # Generic V1.1 fields used when internal slot 3 contains model A/D.
        "pack_soc": "e_pack_soc",
        "mppt_sensors": "e_mppt_sensors",
    },
}

MODEL_FIELDS: dict[str, dict[str, str]] = {
    "A": SLOT_FIELDS["A"],
    "D": SLOT_FIELDS["D"],
    "E": SLOT_FIELDS["E"],
}

MODEL_DEFAULTS = {
    model: {
        field: DEFAULTS.get(config_key)
        for field, config_key in fields.items()
        if config_key in DEFAULTS
    }
    for model, fields in MODEL_FIELDS.items()
}

MODEL_MODULE_KWH = {"A": 2.08, "D": 2.56}
MODEL_DEFAULT_MODULES = {"A": 2, "D": 2}
MODEL_PREFERRED_W = {"A": 1100.0, "D": 1300.0, "E": 1300.0}
MODEL_MAXIMUM_W = {"A": 1500.0, "D": 2500.0, "E": 2500.0}
MODEL_REFERENCE_AC_KWH = {"E": 5.15}
MODEL_REFERENCE_AC_PER_MODULE_KWH = {"A": 1.885, "D": 2.5}


def legacy_instances(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return instance records for a V1.0 model-keyed config entry."""
    enabled = config.get(CONF_ENABLED_MODELS, ["A", "E"])
    if not isinstance(enabled, list):
        enabled = ["A", "E"]
    instances: list[dict[str, Any]] = []
    for model in SLOT_KEYS:
        if model not in enabled:
            continue
        fields = {
            field: config.get(config_key, DEFAULTS.get(config_key))
            for field, config_key in MODEL_FIELDS[model].items()
        }
        configured_packs = fields.get("pack_soc")
        modules = (
            max(1, min(6, len(configured_packs)))
            if model in MODEL_DEFAULT_MODULES and isinstance(configured_packs, list)
            else MODEL_DEFAULT_MODULES.get(model, 1)
        )
        fields.update(
            {
                "id": f"venus_{model.lower()}_1",
                "name": f"Venus {model}",
                "model": model,
                "modules": modules,
            }
        )
        instances.append(fields)
    return instances


def storage_instances(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return up to three validated storage instances in stable slot order."""
    raw = config.get(CONF_STORAGE_INSTANCES)
    if not isinstance(raw, list):
        return legacy_instances(config)
    result: list[dict[str, Any]] = []
    for index, value in enumerate(raw[:3]):
        if not isinstance(value, dict) or value.get("model") not in SLOT_KEYS:
            continue
        model = str(value["model"])
        item = dict(MODEL_DEFAULTS[model])
        item.update(value)
        item["id"] = str(item.get("id") or f"speicher_{index + 1}")
        item["name"] = str(item.get("name") or f"Venus {model} {index + 1}")
        item["modules"] = max(
            1,
            min(6, int(float(item.get("modules", MODEL_DEFAULT_MODULES.get(model, 1))))),
        )
        result.append(item)
    return result or legacy_instances(config)


def normalize_config(config: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Map instance records onto the three proven internal planner slots."""
    instances = storage_instances(config)
    normalized = dict(config)
    normalized[CONF_ENABLED_MODELS] = list(SLOT_KEYS[: len(instances)])
    normalized["slot_models"] = {}
    normalized["slot_names"] = {}
    normalized["slot_ids"] = {}
    for slot, instance in zip(SLOT_KEYS, instances, strict=False):
        normalized["slot_models"][slot] = instance["model"]
        normalized["slot_names"][slot] = instance["name"]
        normalized["slot_ids"][slot] = instance["id"]
        for field, config_key in SLOT_FIELDS[slot].items():
            value = instance.get(field)
            if value not in (None, "", []):
                normalized[config_key] = value
            else:
                normalized.pop(config_key, None)
    return normalized, instances


def nominal_capacity(model: str, modules: int = 1) -> float:
    """Return the model-defined nominal capacity in kWh."""
    if model in MODEL_MODULE_KWH:
        return round(MODEL_MODULE_KWH[model] * max(1, min(6, modules)), 2)
    return 5.12


def calibration_reference_energy(model: str, modules: int = 1) -> float | None:
    """Return measured AC energy including losses before a device has learned."""
    if model in MODEL_REFERENCE_AC_PER_MODULE_KWH:
        return round(
            MODEL_REFERENCE_AC_PER_MODULE_KWH[model]
            * max(1, min(6, modules)),
            4,
        )
    return MODEL_REFERENCE_AC_KWH.get(model)
