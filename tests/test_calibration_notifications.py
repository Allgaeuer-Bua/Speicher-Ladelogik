"""Execute the coordinator's notification/persistence methods through restarts."""
import ast
import asyncio
import importlib
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).parents[1] / 'custom_components/speicher_ladelogik_ae'
pkg = types.ModuleType('notice_fixture')
pkg.__path__ = [str(ROOT)]
sys.modules['notice_fixture'] = pkg
notices = importlib.import_module('notice_fixture.calibration_notifications')
persistence = importlib.import_module('notice_fixture.persistence')

# Exercise the actual coordinator methods with fake HA storage/services.
# No Home Assistant installation is required by the project's CI runner.
source = ast.parse((ROOT / 'coordinator.py').read_text())
coordinator = next(n for n in source.body if isinstance(n, ast.ClassDef))
methods = [n for n in coordinator.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
           and n.name in {'_schedule_state_save', '_async_load_state', '_async_update_calibration_notification'}]
namespace = dict(Any=object, notification_signature=notices.notification_signature,
                 restored_notification_signature=notices.restored_notification_signature,
                 migrate_legacy_day_class_goals=lambda *args: None, EARLY_DAY_CLASSES=())
exec(compile(ast.Module(body=methods, type_ignores=[]), str(ROOT / 'coordinator.py'), 'exec'), namespace)


def clone(value):
    return json.loads(json.dumps(value))


class Store:
    def __init__(self, value):
        self.value = clone(value)

    async def async_load(self):
        return clone(self.value)

    def async_delay_save(self, callback, delay):
        self.value = clone(callback())


class Harness:
    def __init__(self, stored=None):
        self._stability_store = Store(stored or {'control': {'mode': 'Automatik'}, 'stability': {}})
        self._stored_stability = {}
        self._control = {}
        self._state_loaded = False
        self._calibration_notification_signature = None
        self.sent = []
        self.failed = False

    def _sync_model_controls(self):
        pass

    async def _async_update_manual_notification(self):
        pass

    def storage_name(self, battery):
        return 'Venus ' + battery

    async def _async_notification(self, *args):
        if self.failed:
            raise RuntimeError('delivery failed')
        self.sent.append(args)

    async def _async_dismiss_notification(self, *args):
        pass


for name in ('_schedule_state_save', '_async_load_state', '_async_update_calibration_notification'):
    setattr(Harness, name, namespace[name])


def terminal(stamp=100, phase='cancelled'):
    return dict(batterie='E', phase=phase, phase_seit_ts=stamp, start_ts=50, ende_ts=90,
                grund_code='cancel', grund='Vom Benutzer beendet', auftraege=[])


def run(awaitable):
    return asyncio.run(awaitable)


def test_terminal_notification_survives_json_storage_and_multiple_restarts():
    h = Harness()
    run(h._async_load_state())
    data = {'calibration': terminal()}
    run(h._async_update_calibration_notification(data))
    assert len(h.sent) == 1
    for _ in range(3):
        h = Harness(h._stability_store.value)
        run(h._async_load_state())
        run(h._async_update_calibration_notification(data))
        assert not h.sent
    # A distinct run ending in the same phase must still be reported.
    run(h._async_update_calibration_notification({'calibration': terminal(200)}))
    assert len(h.sent) == 1


def test_upgrade_does_not_replay_old_aborted_session_but_new_abort_is_reported():
    session = persistence.read_session('')
    session.update(p='cancelled', b='E', t=100, s=50, x=90, r='cancel')
    h = Harness({'control': {'mode': 'Automatik', 'kalibrierung_sitzung': persistence.encode_session(session)}, 'stability': {}})
    run(h._async_load_state())
    run(h._async_update_calibration_notification({'calibration': terminal()}))
    assert not h.sent
    run(h._async_update_calibration_notification({'calibration': terminal(200)}))
    assert len(h.sent) == 1


def test_startup_cancellation_of_active_run_is_not_silenced():
    session = persistence.read_session('')
    session.update(p='charge', b='E', t=100, s=50, x=90)
    h = Harness({'control': {'mode': 'Automatik', 'kalibrierung_sitzung': persistence.encode_session(session)}, 'stability': {}})
    run(h._async_load_state())
    run(h._async_update_calibration_notification({'calibration': terminal(200)}))
    assert len(h.sent) == 1


def test_active_jobs_do_not_replay_on_restart_and_failed_delivery_is_retryable():
    data = {'calibration': {'auftraege': [{'batterie': 'E', 'name': 'Venus E', 'phase': 'charge', 'grund': 'Lädt'}]}}
    h = Harness()
    run(h._async_load_state())
    h.failed = True
    try:
        run(h._async_update_calibration_notification(data))
    except RuntimeError:
        pass
    assert h._calibration_notification_signature is None
    h.failed = False
    run(h._async_update_calibration_notification(data))
    assert len(h.sent) == 1
    h = Harness(h._stability_store.value)
    run(h._async_load_state())
    run(h._async_update_calibration_notification(data))
    assert not h.sent
    run(h._async_update_calibration_notification({'calibration': terminal(200, 'done')}))
    assert len(h.sent) == 1
