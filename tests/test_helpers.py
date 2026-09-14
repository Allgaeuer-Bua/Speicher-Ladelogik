"""Tests for pure Speicher-Ladelogik helpers."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

HELPERS_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "speicher_ladelogik"
    / "helpers.py"
)
SPEC = spec_from_file_location("speicher_ladelogik_helpers", HELPERS_PATH)
assert SPEC is not None and SPEC.loader is not None
HELPERS = module_from_spec(SPEC)
SPEC.loader.exec_module(HELPERS)

as_number = HELPERS.as_number
is_usable_state = HELPERS.is_usable_state
power_in_watts = HELPERS.power_in_watts


def test_as_number() -> None:
    assert as_number("12.5") == 12.5
    assert as_number("unknown") is None
    assert as_number(float("nan")) is None


def test_power_in_watts() -> None:
    assert power_in_watts("1250", "W") == 1250
    assert power_in_watts("1.25", "kW") == 1250
    assert power_in_watts("1", "V") is None


def test_usable_state() -> None:
    assert is_usable_state("0") is True
    assert is_usable_state("unknown") is False
    assert is_usable_state("unavailable") is False
