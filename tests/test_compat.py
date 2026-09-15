"""Tests for the V2.2.1 compatibility bridge."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

COMPAT_PATH = (
    Path(__file__).parents[1] / "custom_components" / "speicher_ladelogik" / "compat.py"
)
SPEC = spec_from_file_location("speicher_ladelogik_compat", COMPAT_PATH)
assert SPEC is not None and SPEC.loader is not None
COMPAT = module_from_spec(SPEC)
SPEC.loader.exec_module(COMPAT)

compatibility_entity_ids = COMPAT.compatibility_entity_ids
first_existing_state = COMPAT.first_existing_state
get_state_with_legacy_fallback = COMPAT.get_state_with_legacy_fallback
legacy_entity_id = COMPAT.legacy_entity_id


class FakeStates:
    """Small state-machine replacement for pure compatibility tests."""

    def __init__(self, states: dict[str, object]) -> None:
        self._states = states

    def get(self, entity_id: str):
        return self._states.get(entity_id)


def test_legacy_entity_id_for_planning_entities() -> None:
    assert (
        legacy_entity_id("sensor.speicher_ladelogik_planung")
        == "sensor.pv_ladelogik_planung"
    )
    assert (
        legacy_entity_id("sensor.speicher_ladelogik_kalibrierung_planung")
        == "sensor.pv_kalibrierung_planung"
    )


def test_legacy_entity_id_for_session_and_settings() -> None:
    assert (
        legacy_entity_id("input_select.speicher_ladelogik_betriebsart")
        == "input_select.pv_ladelogik_betriebsart"
    )
    assert (
        legacy_entity_id("input_text.speicher_ladelogik_kalibrierung_sitzung")
        == "input_text.pv_kalibrierung_sitzung"
    )
    assert (
        legacy_entity_id("input_number.speicher_ladelogik_ziel_soc")
        == "input_number.pv_ladelogik_ziel_soc"
    )
    assert (
        legacy_entity_id("input_boolean.speicher_ladelogik_kalibrierung_e_freigegeben")
        == "input_boolean.pv_kalibrierung_e_freigegeben"
    )


def test_special_initialisation_helper_mapping() -> None:
    assert (
        legacy_entity_id("input_boolean.speicher_ladelogik_v1_beta_1_initialisiert")
        == "input_boolean.pv_ladelogik_rc5_initialisiert"
    )


def test_current_entity_has_priority() -> None:
    current = object()
    legacy = object()
    states = FakeStates(
        {
            "input_select.speicher_ladelogik_betriebsart": current,
            "input_select.pv_ladelogik_betriebsart": legacy,
        }
    )
    assert (
        get_state_with_legacy_fallback(
            states, "input_select.speicher_ladelogik_betriebsart"
        )
        is current
    )


def test_legacy_entity_is_used_as_fallback() -> None:
    legacy = object()
    states = FakeStates({"input_select.pv_ladelogik_betriebsart": legacy})
    assert (
        get_state_with_legacy_fallback(
            states, "input_select.speicher_ladelogik_betriebsart"
        )
        is legacy
    )


def test_first_existing_state_reports_reference_entity() -> None:
    legacy = object()
    states = FakeStates({"sensor.pv_ladelogik_planung": legacy})
    state, entity_id = first_existing_state(
        states,
        (
            "sensor.speicher_ladelogik_planung",
            "sensor.pv_ladelogik_planung",
        ),
    )
    assert state is legacy
    assert entity_id == "sensor.pv_ladelogik_planung"


def test_tracking_contains_legacy_entities_once() -> None:
    aliases = compatibility_entity_ids(
        (
            "sensor.speicher_ladelogik_planung",
            "sensor.speicher_ladelogik_planung",
            "input_number.speicher_ladelogik_ziel_soc",
        )
    )
    assert aliases == [
        "sensor.pv_ladelogik_planung",
        "input_number.pv_ladelogik_ziel_soc",
    ]
