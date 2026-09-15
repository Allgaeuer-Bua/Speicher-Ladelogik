"""Tests for state-based register stability."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

STABILITY_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "speicher_ladelogik"
    / "stability.py"
)
SPEC = spec_from_file_location("speicher_ladelogik_stability", STABILITY_PATH)
assert SPEC is not None and SPEC.loader is not None
STABILITY = module_from_spec(SPEC)
SPEC.loader.exec_module(STABILITY)

stable_charge_limit = STABILITY.stable_charge_limit
target_latch = STABILITY.target_latch
peer_discharge_release = STABILITY.peer_discharge_release


def test_target_is_latched_at_device_goal() -> None:
    reached, _ = target_latch(
        goal=100,
        soc=100,
        lowest_soc=100,
        prior_latched=True,
        prior_goal=100,
    )
    assert reached is True


def test_target_latch_releases_immediately_below_device_goal() -> None:
    reached, _ = target_latch(
        goal=100,
        soc=97.9,
        lowest_soc=97.9,
        prior_latched=True,
        prior_goal=100,
    )
    assert reached is False


def test_target_latch_does_not_survive_changed_goal() -> None:
    reached, _ = target_latch(
        goal=100,
        soc=80,
        lowest_soc=80,
        prior_latched=True,
        prior_goal=80,
    )
    assert reached is False


def test_peer_discharge_is_released_once_at_fourteen_percent() -> None:
    released, _ = peer_discharge_release(
        phase="drain",
        target_soc=14,
        highest_pack_soc=14,
        prior_released=False,
    )
    assert released is True


def test_peer_release_waits_for_highest_pack() -> None:
    released, _ = peer_discharge_release(
        phase="drain",
        target_soc=13.8,
        highest_pack_soc=14.2,
        prior_released=False,
    )
    assert released is False


def test_peer_release_latch_does_not_flap() -> None:
    released, _ = peer_discharge_release(
        phase="drain",
        target_soc=15,
        highest_pack_soc=15,
        prior_released=True,
    )
    assert released is True


def test_peer_release_resets_outside_drain() -> None:
    released, _ = peer_discharge_release(
        phase="wait",
        target_soc=13,
        highest_pack_soc=13,
        prior_released=True,
    )
    assert released is False


def test_limit_is_kept_during_short_surplus_pause() -> None:
    value, held, _ = stable_charge_limit(
        raw_limit=0,
        previous_limit=1100,
        current_cap=1500,
        eligible=True,
        target_reached=False,
        within_window=True,
        planner_status="Keine PV-Ladechance",
        safety_stop=False,
    )
    assert value == 1100
    assert held is True


def test_lower_nonzero_limit_does_not_cause_an_extra_write() -> None:
    value, held, _ = stable_charge_limit(
        raw_limit=500,
        previous_limit=1100,
        current_cap=1500,
        eligible=True,
        target_reached=False,
        within_window=True,
        planner_status="Fahrplanladen",
        safety_stop=False,
    )
    assert value == 1100
    assert held is True


def test_hardware_cap_reduction_is_applied() -> None:
    value, held, _ = stable_charge_limit(
        raw_limit=500,
        previous_limit=1100,
        current_cap=500,
        eligible=True,
        target_reached=False,
        within_window=True,
        planner_status="Fahrplanladen",
        safety_stop=False,
    )
    assert value == 500
    assert held is False


def test_deliberate_peak_hold_sets_zero_immediately() -> None:
    value, held, _ = stable_charge_limit(
        raw_limit=0,
        previous_limit=1100,
        current_cap=1500,
        eligible=True,
        target_reached=False,
        within_window=True,
        planner_status="Platz für Mittagsspitze halten",
        safety_stop=False,
    )
    assert value == 0
    assert held is False


def test_safety_stop_sets_zero_immediately() -> None:
    value, held, _ = stable_charge_limit(
        raw_limit=1100,
        previous_limit=1100,
        current_cap=1500,
        eligible=True,
        target_reached=False,
        within_window=True,
        planner_status="Fahrplanladen",
        safety_stop=True,
    )
    assert value == 0
    assert held is False


def test_target_keeps_register_but_window_end_sets_zero() -> None:
    target_value, _, _ = stable_charge_limit(
        raw_limit=500,
        previous_limit=500,
        current_cap=500,
        eligible=True,
        target_reached=True,
        within_window=True,
        planner_status="Fahrplanladen",
        safety_stop=False,
    )
    window_value, _, _ = stable_charge_limit(
        raw_limit=0,
        previous_limit=500,
        current_cap=500,
        eligible=True,
        target_reached=False,
        within_window=False,
        planner_status="Keine PV-Ladechance",
        safety_stop=False,
    )
    assert target_value == 500
    assert window_value == 0
