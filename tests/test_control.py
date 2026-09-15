"""Tests for guarded register-write validation."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

CONTROL_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "speicher_ladelogik"
    / "control.py"
)
SPEC = spec_from_file_location("speicher_ladelogik_control", CONTROL_PATH)
assert SPEC is not None and SPEC.loader is not None
CONTROL = module_from_spec(SPEC)
SPEC.loader.exec_module(CONTROL)


def test_valid_target() -> None:
    assert (
        CONTROL.validate_number_target(
            current=0, minimum=0, maximum=2500, step=50, target=1300
        )
        is None
    )


def test_target_outside_device_range_is_rejected() -> None:
    assert CONTROL.validate_number_target(
        current=0, minimum=0, maximum=1500, step=50, target=2500
    )


def test_target_off_step_is_rejected() -> None:
    assert CONTROL.validate_number_target(
        current=0, minimum=0, maximum=2500, step=50, target=525
    )


def test_write_tolerance() -> None:
    assert CONTROL.write_needed(500, 524) is False
    assert CONTROL.write_needed(500, 525) is True
