"""AC receipt must work in standby, with episode-based notifications."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('telemetry', Path(__file__).parents[1] / 'custom_components/speicher_ladelogik_ae/telemetry.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
feedback = module.ac_feedback


def call(now, prior=None, **changes):
    args = dict(now=now, requested=True, fresh=False, inverter_status=None,
                inverter_fresh=False, prior=prior or {})
    args.update(changes)
    return feedback(**args)


def test_fresh_zero_and_discharge_reports_never_need_charging_confirmation():
    for state in ('Standby', 'Discharge', 'Charge', None):
        prior = {}
        for now in (0, 180, 3600):
            prior = call(now, prior, fresh=True, inverter_status=state, inverter_fresh=state is not None)
            assert prior['confirmed'] and not prior['issue'] and not prior['notify']


def test_stale_ac_warns_once_even_with_current_standby_and_ac_recovers():
    first = call(0, inverter_status='Standby', inverter_fresh=True)
    warning = call(180, first, inverter_status='Standby', inverter_fresh=True)
    assert warning['notify'] and 'AC-Sensor prüfen' in warning['message']
    for now in (195, 900, 3600):
        warning = call(now, dict(warning), inverter_status='Standby', inverter_fresh=True)
        assert warning['issue'] and not warning['notify'] and not warning['blocked']
    recovered = call(3615, warning, fresh=True)
    assert recovered['resolved'] and not recovered['issue']
    missing_again = call(4000, recovered)
    assert not missing_again['notify']
    assert call(4180, missing_again)['notify']


def test_old_standby_cannot_hide_missing_communication_or_repeat_warning():
    missing = call(0, inverter_status='Standby', inverter_fresh=False)
    warning = call(180, missing, inverter_status='Standby', inverter_fresh=False)
    assert warning['notify'] and 'Datenverbindung prüfen' in warning['message']
    assert not call(400, warning, inverter_status='Charge', inverter_fresh=True)['notify']
    stopped = call(415, warning, requested=False)
    assert stopped['resolved'] and not stopped['issue']


def test_earlier_success_does_not_mask_a_later_lost_ac_stream():
    confirmed = call(0, fresh=True)
    stale = call(100, confirmed)
    assert not stale['confirmed'] and not stale['notify']
    assert call(280, stale)['notify']
