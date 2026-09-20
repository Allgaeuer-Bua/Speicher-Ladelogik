"""Tests for the V1.1 storage-instance model."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).parents[1] / "custom_components" / "speicher_ladelogik"

homeassistant = types.ModuleType("homeassistant")
homeassistant_const = types.ModuleType("homeassistant.const")


class _Platform:
    SENSOR = "sensor"
    SWITCH = "switch"
    SELECT = "select"
    NUMBER = "number"
    BUTTON = "button"


homeassistant_const.Platform = _Platform
sys.modules.setdefault("homeassistant", homeassistant)
sys.modules.setdefault("homeassistant.const", homeassistant_const)

package = types.ModuleType("speicher_ladelogik_test")
package.__path__ = [str(ROOT)]
sys.modules.setdefault("speicher_ladelogik_test", package)


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(
        f"speicher_ladelogik_test.{name}", ROOT / filename
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_load("const", "const.py")
STORAGE = _load("storage", "storage.py")


def test_model_capacities_are_derived_from_up_to_six_modules() -> None:
    assert STORAGE.nominal_capacity("A", 1) == 2.08
    assert STORAGE.nominal_capacity("A", 6) == 12.48
    assert STORAGE.nominal_capacity("A", 8) == 12.48
    assert STORAGE.nominal_capacity("D", 1) == 2.56
    assert STORAGE.nominal_capacity("D", 6) == 15.36
    assert STORAGE.nominal_capacity("E", 1) == 5.12


def test_calibration_references_include_losses_without_extra_energy() -> None:
    assert STORAGE.calibration_reference_energy("A", 2) == 3.77
    assert STORAGE.calibration_reference_energy("A", 6) == 11.31
    assert STORAGE.calibration_reference_energy("E", 1) == 5.15


def test_three_equal_models_receive_three_independent_slots() -> None:
    instances = [
        {
            "id": f"venus_e_{index}",
            "name": f"Venus E {index}",
            "model": "E",
            "soc": f"sensor.e_{index}_soc",
            "ac_power": f"sensor.e_{index}_power",
            "charge_limit": f"number.e_{index}_charge",
        }
        for index in range(1, 4)
    ]
    normalized, parsed = STORAGE.normalize_config(
        {"storage_instances": instances}
    )

    assert len(parsed) == 3
    assert normalized["enabled_models"] == ["A", "D", "E"]
    assert normalized["slot_models"] == {"A": "E", "D": "E", "E": "E"}
    assert normalized["a_soc"] == "sensor.e_1_soc"
    assert normalized["d_soc"] == "sensor.e_2_soc"
    assert normalized["e_soc"] == "sensor.e_3_soc"


def test_pack_model_can_use_the_third_internal_slot() -> None:
    instances = [
        {"id": "e1", "name": "E 1", "model": "E", "soc": "sensor.e1"},
        {"id": "e2", "name": "E 2", "model": "E", "soc": "sensor.e2"},
        {
            "id": "a1",
            "name": "A 1",
            "model": "A",
            "soc": "sensor.a1",
            "pack_soc": ["sensor.a1_pack_1", "sensor.a1_pack_2"],
            "drift": ["sensor.a1_drift_1", "sensor.a1_drift_2"],
            "modules": 2,
        },
    ]
    normalized, _parsed = STORAGE.normalize_config(
        {"storage_instances": instances}
    )

    assert normalized["slot_models"]["E"] == "A"
    assert normalized["e_pack_soc"] == [
        "sensor.a1_pack_1",
        "sensor.a1_pack_2",
    ]
    assert normalized["e_cell_drift"] == [
        "sensor.a1_drift_1",
        "sensor.a1_drift_2",
    ]


def test_legacy_entries_migrate_without_changing_physical_entities() -> None:
    instances = STORAGE.legacy_instances(
        {
            "enabled_models": ["A", "E"],
            "a_soc": "sensor.existing_a",
            "e_soc": "sensor.existing_e",
            "a_pack_soc": ["sensor.a_pack_1", "sensor.a_pack_2"],
        }
    )

    assert [item["model"] for item in instances] == ["A", "E"]
    assert instances[0]["soc"] == "sensor.existing_a"
    assert instances[0]["modules"] == 2
    assert instances[1]["soc"] == "sensor.existing_e"
