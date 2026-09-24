"""The displayed outcome must belong to the latest successful calibration."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "speicher_ladelogik"
    / "calibration_results.py"
)
SPEC = spec_from_file_location("speicher_ladelogik_calibration_results", PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_completed_run_keeps_its_own_energy_and_end_drift() -> None:
    control = {"lernspeicher": {"history": [
        {"battery": "A", "result": "done", "end": 1000, "ac_kwh": 3.913,
         "drift_after_mv": [9, 2], "learning_valid": True},
        {"battery": "A", "result": "cancelled", "end": 1100, "ac_kwh": 0.2},
        {"battery": "E", "result": "done", "end": 1000, "ac_kwh": 5.15},
    ]}}
    assert MODULE.last_successful_result(control, "A", 1001) == {
        "end_ts": 1001, "ac_kwh": 3.913, "learned": True,
        "drift_after_mv": [9.0, 2.0],
        "drift_top_start_mv": [], "drift_top_change_mv": [],
    }


def test_old_success_does_not_inherit_an_unrelated_drift_sample() -> None:
    control = {"kalibrierung_a_letzte_energie": 3.77, "lernspeicher": {
        "history": [{"battery": "A", "result": "done", "end": 1000,
                     "drift_after_mv": [4], "learning_valid": True}]
    }}
    assert MODULE.last_successful_result(control, "A", 2000) == {
        "end_ts": 2000, "ac_kwh": 3.77, "learned": None,
        "drift_after_mv": [],
        "drift_top_start_mv": [], "drift_top_change_mv": [],
    }


def test_missing_sensor_values_are_not_shown_as_zero() -> None:
    control = {"lernspeicher": {"history": [
        {"battery": "E", "result": "done", "end": 1000,
         "ac_kwh": None, "drift_after_mv": [None, "unavailable"],
         "learning_valid": False}
    ]}}
    assert MODULE.last_successful_result(control, "E", 1000) == {
        "end_ts": 1000, "ac_kwh": None, "learned": False,
        "drift_after_mv": [None, None],
        "drift_top_start_mv": [], "drift_top_change_mv": [],
    }
    assert MODULE.last_successful_result(control, "A", None) is None


def test_only_comparable_top_soc_drift_samples_form_a_trend() -> None:
    control = {"lernspeicher": {"history": [{
        "battery": "A", "result": "done", "end": 1000,
        "drift_top_start_mv": [9, None], "drift_after_mv": [7, 2],
    }]}}
    result = MODULE.last_successful_result(control, "A", 1000)
    assert result["drift_top_start_mv"] == [9.0, None]
    assert result["drift_top_change_mv"] == [-2.0, None]
