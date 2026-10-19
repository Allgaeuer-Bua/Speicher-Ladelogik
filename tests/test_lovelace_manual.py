"""Manual drafts must be validated before any coordinator option changes."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_spec = spec_from_file_location("manual_validation", Path(__file__).parents[1] / "custom_components/speicher_ladelogik_ae/control.py")
control = module_from_spec(_spec)
_spec.loader.exec_module(control)


def test_complete_manual_draft_is_independent_and_has_no_soc_target():
    result = control.manual_control_update("A", "A", True, 1100, 1500)
    assert result == {"manuell_a_aktiv": True, "manuell_laden_a_w": 1100, "manuell_entladen_a_w": 1500}
    assert all("soc" not in key and "_e_" not in key for key in result)


def test_deactivation_needs_no_device_measurement_or_new_limits():
    assert control.manual_control_update("E", "E", False, None, None) == {"manuell_e_aktiv": False}


def test_bad_manual_drafts_are_rejected_whole():
    for charge, discharge in ((None, 1500), (1100, None), (-50, 1500), (1550, 1500),
                              (1101, 1500), (float("nan"), 1500), (1100, float("inf"))):
        try:
            control.manual_control_update("A", "A", True, charge, discharge)
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError((charge, discharge))


def test_venus_e_keeps_its_own_limit():
    result = control.manual_control_update("E", "E", True, 2500, 1950)
    assert result["manuell_laden_e_w"] == 2500
    assert result["manuell_entladen_e_w"] == 1950
