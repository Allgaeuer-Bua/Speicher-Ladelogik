"""Regression scenarios collected from the v1.2.2 field audit."""
import ast
import copy
import importlib.util
import sys
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parents[1] / 'custom_components' / 'speicher_ladelogik'
spec = importlib.util.spec_from_file_location('release_fixture', Path(__file__).with_name('test_parallel_calibration.py'))
fx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fx)
fx._dt.utcnow = lambda: datetime.fromtimestamp(fx.NOW, timezone.utc)
STUBS = {'calibration_fixture': fx._package, 'homeassistant': fx._ha, 'homeassistant.core': fx._core,
         'homeassistant.util': fx._util, 'homeassistant.util.dt': fx._dt}
with patch.dict(sys.modules, STUBS):
    runtime = import_module('calibration_fixture.runtime')
    estimates = import_module('calibration_fixture.estimates')

source = ast.parse((ROOT / 'planner.py').read_text())
calculate = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == 'calculate_plan')
ENTITIES = ast.literal_eval(next(n.value for n in calculate.body if isinstance(n, ast.Assign)
                          and any(isinstance(t, ast.Name) and t.id == 'SLOT_ENTITIES' for t in n.targets)))


def run(hass, payload):
    with patch.dict(sys.modules, STUBS):
        return fx.planner.calculate_plan(hass, payload)


def set_value(hass, key, value):
    old = hass.states.states.get(key)
    hass.states.states[key] = fx.state(value, fx.NOW, **(old.attributes if old else {}))


def test_native_day_class_settings_reach_the_real_planner():
    controls = copy.deepcopy(runtime.CONTROL_DEFAULTS)
    controls.update(mode='Automatik', fruehes_ladeziel_a_stark_soc=60., fruehes_ladeziel_e_stark_soc=0.)
    hass, payload = fx.scenario(primary_phase='idle', secondary_phase='idle')
    with patch.dict(sys.modules, STUBS):
        hass.states.states.update(runtime.planner_states(controls))
    out = run(hass, payload)
    assert out['plan']['tagesklasse'] == 'stark'
    assert out['plan']['fruehe_soc_ziele_prozent'] == {'A': 60., 'E': 0.}


def test_weak_morning_does_not_turn_a_sunny_day_into_a_weak_class():
    controls = copy.deepcopy(runtime.CONTROL_DEFAULTS)
    controls.update(mode='Automatik', fruehes_ladeziel_a_stark_soc=50.,
                    fruehes_ladeziel_e_stark_soc=50.,
                    bevorzugte_ladeleistung_a_w=1100,
                    bevorzugte_ladeleistung_e_w=1300)
    hass, payload = fx.scenario(primary_phase='idle', secondary_phase='idle', pv=6000)
    set_value(hass, 'sensor.pv_produktion_tag', .2)
    for direction in ('sw', 'so', 'no'):
        entity = f'sensor.{direction}_energy_production_today'
        buckets = {datetime.fromtimestamp(fx.DAY + index * 900, timezone.utc).isoformat():
                   (100 if 24 <= index < 28 else 750 if 28 <= index < 72 else 0)
                   for index in range(96)}
        hass.states.states[entity] = fx.state(33.4, fx.NOW, unit='kWh', wh_period_15m=buckets)
    with patch.dict(sys.modules, STUBS):
        hass.states.states.update(runtime.planner_states(controls))
    out = run(hass, payload)['plan']
    assert out['prognose_heute_roh_kwh'] > 90
    assert out['prognose_heute_erwartet_kwh'] > 85
    assert out['tagesklasse'] == 'stark'
    assert out['fahrplan_ladegrenze_roh_venus_a_w'] <= 1100
    assert out['fahrplan_ladegrenze_roh_venus_e_w'] <= 1300


def test_recovery_after_missing_data_may_resume_in_the_same_slot():
    hass, payload = fx.scenario(primary_phase='idle', secondary_phase='idle', pv=6000)
    payload['prior_plan'] = {
        'version': '1.2.3', 'berechnet_ts': fx.NOW - 20,
        'betriebsart': 'Automatik', 'regelung_aktiv': True,
        'daten_gueltig': False,
        'fahrplan_slot_start_ts': int(fx.NOW // 900) * 900,
        'fahrplan_slot_aktiv_venus_a': False,
        'fahrplan_ladegrenze_stabil_venus_a_w': 0,
    }
    controls = copy.deepcopy(runtime.CONTROL_DEFAULTS)
    controls.update(mode='Automatik', fruehes_ladeziel_a_stark_soc=50.)
    with patch.dict(sys.modules, STUBS):
        hass.states.states.update(runtime.planner_states(controls))
    plan = run(hass, payload)['plan']
    assert plan['fahrplan_slot_verriegelt'] is False
    assert plan['fahrplan_ladegrenze_stabil_venus_a_w'] > 0


def test_venus_e_in_internal_d_slot_uses_its_own_preferred_limit():
    hass, payload = fx.scenario(primary_phase='idle', secondary_phase='idle', pv=6000)
    for field, old_id in ENTITIES['E'].items():
        if old_id in hass.states.states:
            hass.states.states[ENTITIES['D'][field]] = hass.states.states.pop(old_id)
    payload.update(battery_keys=['A', 'D'], slot_models={'A': 'A', 'D': 'E'},
                   slot_names={'A': 'Venus A', 'D': 'Venus E'})
    controls = copy.deepcopy(runtime.CONTROL_DEFAULTS)
    controls.update(mode='Automatik', fruehes_ladeziel_a_stark_soc=50.,
                    fruehes_ladeziel_d_stark_soc=50.,
                    bevorzugte_ladeleistung_a_w=1100,
                    bevorzugte_ladeleistung_d_w=1300)
    with patch.dict(sys.modules, STUBS):
        hass.states.states.update(runtime.planner_states(controls))
    plan = run(hass, payload)['plan']
    assert plan['fruehe_soc_ziele_prozent'] == {'A': 50., 'D': 50.}
    assert plan['fahrplan_ladegrenze_roh_venus_a_w'] == 1100
    assert plan['fahrplan_ladegrenze_roh_venus_d_w'] == 1300


def test_calibration_pauses_on_real_import_despite_own_charging_draw():
    hass, payload = fx.scenario(pv=1000, live_load=900, secondary_phase='idle')
    set_value(hass, 'sensor.stromzahler_leistung', 400)
    out = run(hass, payload)
    assert out['plan']['netto_ueberschuss_w'] == 100
    assert out['calibration']['phase'] == 'paused'
    assert out['plan']['soll_ladegrenze_venus_a_w'] == 0


def test_parallel_start_does_not_spend_the_first_batterys_power_twice():
    hass, payload = fx.scenario(pv=2000, live_load=1000)
    set_value(hass, 'sensor.stromzahler_leistung', -500)
    out = run(hass, payload)
    assert out['calibration']['phase'] == 'charge'
    assert fx.persistence.read_session(out['parallel_session'])['p'] == 'wait'
    assert len(out['calibration']['auftraege']) == 2
    assert {j['phase'] for j in out['calibration']['auftraege']} == {'charge', 'wait'}


def test_internal_slot_d_restores_charge_and_discharge_independently():
    hass, payload = fx.scenario(primary_phase='idle', secondary_phase='idle')
    for field, old_id in ENTITIES['E'].items():
        if old_id in hass.states.states:
            hass.states.states[ENTITIES['D'][field]] = hass.states.states.pop(old_id)
    payload.update(battery_keys=['A', 'D'], slot_models={'A': 'A', 'D': 'E'},
                   slot_names={'A': 'Venus A', 'D': 'Venus E Keller'}, parallel_calibration=False, parallel_session='')
    session = fx.persistence.read_session('')
    session.update(p='restore', b='D', r='cancelled', s=fx.NOW - 1000, x=fx.NOW + 1000, z=1)
    set_value(hass, 'input_text.speicher_ladelogik_kalibrierung_sitzung', fx.persistence.encode_session(session))
    set_value(hass, 'input_text.speicher_ladelogik_kalibrierung_sicherung', 'backup2|-1|1300|-1|-1|2500|-1')
    set_value(hass, 'input_text.speicher_ladelogik_sicherung', 'backup2|0|0|-1|1500|2500|-1')
    set_value(hass, ENTITIES['D']['charge'], 500)
    set_value(hass, ENTITIES['D']['discharge'], 0)
    out = run(hass, payload)
    commands = {cmd['entity']: cmd['value'] for cmd in out['proposed_commands'] if cmd['battery'] == 'D'}
    assert commands == {ENTITIES['D']['charge']: 1300, ENTITIES['D']['discharge']: 2500}
    assert 'Venus E Keller' in out['plan']['status']
    assert out['calibration']['auftraege'][0]['name'] == 'Venus E Keller'
    for key, value in commands.items():
        set_value(hass, key, value)
    set_value(hass, 'input_text.speicher_ladelogik_kalibrierung_sitzung', out['session'])
    out = run(hass, payload)
    assert out['calibration']['phase'] == 'cancelled'


def test_sunny_caps_only_raise_the_storage_that_needs_more_power():
    selected = [n for n in calculate.body if isinstance(n, ast.FunctionDef)
                and n.name in ('split_power', 'simulate', 'minimum_working_caps')]
    scope = {'BATTERY_KEYS': ['A', 'E'], 'BATTERIES': {'A': {'tail': 500}, 'E': {'tail': 1100}}}
    exec(compile(ast.Module(body=selected, type_ignores=[]), 'planner.py', 'exec'), scope)
    rows = [{'t': i * 900, 'wh': 2500} for i in range(96)]
    batteries = {k: {'need': capacity * .84, 'nominal': capacity, 'goal': 100, 'target': capacity * .88}
                 for k, capacity in [('A', 4.16), ('E', 5.12)]}
    caps, result = scope['minimum_working_caps'](rows, 11.25 * 3600, 15 * 3600 + 9 * 60 + 29,
        batteries, {'A': 1100, 'E': 1300}, {'A': 1500, 'E': 2500}, 1000, .9, 11.25 * 3600)
    assert caps == {'A': 1150, 'E': 1300}
    assert result['finish'] is not None


def test_disabling_peak_shaving_removes_the_noon_window_constraint():
    results = []
    for midday in (9, 13):
        hass, payload = fx.scenario(primary_phase='idle', secondary_phase='idle')
        set_value(hass, 'input_boolean.speicher_ladelogik_mittagsspitzen', 'off')
        payload.update(midday_start=fx.DAY + midday * 3600, midday_end=fx.DAY + (midday + 2) * 3600)
        out = run(hass, payload)['plan']
        assert not out['mittagsspitzen_aktiv']
        results.append((out['ladefenster_start_ts'], out['ladefenster_ende_ts'], out['soll_ladeleistung_gesamt_w']))
    assert results[0] == results[1]


def test_configurable_lower_rest_respects_elapsed_time_and_preview():
    phases = []
    for minutes in (0, 120):
        hass, payload = fx.scenario(primary_phase='empty_rest', secondary_phase='idle')
        set_value(hass, 'input_number.speicher_ladelogik_kalibrierung_ruhe_unten_min', minutes)
        out = run(hass, payload)
        phases.append(out['calibration']['phase'])
        assert out['calibration']['ruhedauer_unten_min'] == minutes
        if minutes:
            job = out['calibration']['auftraege'][0]
            assert job['ruhe_verbleibend_s'] == minutes * 60 - 100
            assert job['ladebeginn_voraussichtlich_ts'] >= job['ruhe_ende_ts']
    assert phases == ['wait', 'empty_rest']


def test_configurable_upper_rest_needs_no_pv_and_keeps_separate_release_time():
    for minutes in (0, 120):
        hass, payload = fx.scenario(pv=0, primary_phase='full_rest', secondary_phase='idle')
        set_value(hass, 'input_number.speicher_ladelogik_kalibrierung_ruhe_oben_min', minutes)
        set_value(hass, 'input_text.speicher_ladelogik_kalibrierung_sicherung', 'backup2|-1|-1|-1|-1|-1|-1')
        for key in list(hass.states.states):
            if key.startswith('sensor.marstek_venus_a_soc'):
                set_value(hass, key, 100)
        item = fx.persistence.read_session(hass.states.states['input_text.speicher_ladelogik_kalibrierung_sitzung'].state)
        item['f'] = fx.NOW - 60
        set_value(hass, 'input_text.speicher_ladelogik_kalibrierung_sitzung', fx.persistence.encode_session(item))
        out = run(hass, payload)
        assert out['calibration']['phase'] == ('done' if minutes == 0 else 'full_rest')
        if minutes:
            assert out['calibration']['auftraege'][0]['ruhe_ende_ts'] == item['f'] + minutes * 60


def test_remaining_time_uses_smoothed_actual_power_and_survives_brief_pack_switch():
    estimator = estimates.RemainingTimeEstimator()
    args = dict(power=-1000, fresh=True, soc=50, nominal=4.16, floor=12, goal=100, need=2.08, efficiency=.9)
    assert estimator.estimate('A', now=100, **args)['modus'] == 'messen'
    steady = estimator.estimate('A', now=120, **args)
    assert steady['restzeit_s'] == round(2.08 / .9 * 3600)
    assert estimator.estimate('A', now=135, **{**args, 'power': 0})['restzeit_s'] == steady['restzeit_s']
    assert estimator.estimate('A', now=160, **{**args, 'power': 0})['restzeit_s'] is None
    assert estimator.estimate('A', now=180, **{**args, 'fresh': False})['modus'] == 'unbekannt'


def test_remaining_time_calibration_does_not_add_losses_twice_and_discharge_stops_at_floor():
    estimator = estimates.RemainingTimeEstimator()
    args = dict(power=-500, fresh=True, soc=50, nominal=4.16, floor=12, goal=100, need=2.08, efficiency=.9,
                calibration_ac_remaining=2.)
    estimator.estimate('A', now=100, **args)
    assert estimator.estimate('A', now=120, **args)['restzeit_s'] == 4 * 3600
    args.update(power=500, calibration_ac_remaining=None)
    assert estimator.estimate('A', now=140, **args)['restzeit_s'] is None
    estimate = estimator.estimate('A', now=160, **args)
    assert estimate['modus'] == 'entladen' and estimate['ziel_soc'] == 12
    assert estimate['restzeit_s'] == round(4.16 * .38 * .9 / .5 * 3600)


def coordinator_methods():
    """Load production lifecycle methods without requiring an HA installation."""
    import asyncio
    import logging
    from typing import Any
    tree = ast.parse((ROOT / 'coordinator.py').read_text())
    original = next(n for n in tree.body if isinstance(n, ast.ClassDef))
    names = {'_async_update_data', '_async_apply_control', '_async_set_helper',
             '_async_update_failure_counters', '_async_update_calibration_notification',
             'async_set_mode', 'async_set_control'}
    methods = [n for n in original.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
    with patch.dict(sys.modules, STUBS):
        control = import_module('calibration_fixture.control')
    scope = {**vars(control), 'Any': Any, 'dt_util': fx._dt, '_LOGGER': logging.getLogger(__name__),
             'HELPER_TO_CONTROL': runtime.HELPER_TO_CONTROL, 'CONTROL_DEFAULTS': runtime.CONTROL_DEFAULTS,
             'HomeAssistantError': ValueError, 'asyncio': asyncio}
    # Compile unchanged methods, then bind them on a minimal coordinator harness.
    exec(compile(ast.Module(body=methods, type_ignores=[]), 'coordinator.py', 'exec'), scope)
    return {name: scope[name] for name in names}


def lifecycle_harness(mode='Aus', failed=False):
    import asyncio
    from types import SimpleNamespace
    methods = coordinator_methods()

    class Harness:
        write_enabled = property(lambda self: self._control['mode'] == 'Automatik')
        enabled_models = ('A', 'E')

    for name, method in methods.items():
        setattr(Harness, name, method)
    obj = Harness()
    obj.hass, obj.payload = fx.scenario(primary_phase='charge', secondary_phase='idle')
    obj.hass.bus = SimpleNamespace(async_fire=lambda *args: None)
    obj._control = copy.deepcopy(runtime.CONTROL_DEFAULTS)
    for entity, key in runtime.HELPER_TO_CONTROL.items():
        state = obj.hass.states.get(entity)
        if state is not None and isinstance(obj._control.get(key), str):
            obj._control[key] = state.state
    obj._control.update(mode=mode, rueckgabe_ausstehend=True,
                        kalibrierung_sicherung='backup2|1100|-1|-1|1500|-1|-1',
                        kalibrierung_a_freigegeben=True)
    obj._write_lock = asyncio.Lock()
    obj._last_write_error = None
    obj._pending_request = 'tick'
    obj._calibration_notification_signature = None
    obj.fail_next = failed
    obj.writes = []
    obj._schedule_state_save = lambda: None
    obj.storage_name = lambda key: 'Venus ' + key
    obj._notifications = []

    async def nothing(*args):
        pass

    async def notification(*args):
        obj._notifications.append(args)

    obj._async_load_state = nothing
    obj._async_update_calibration_due_notification = nothing
    obj._async_update_problem_notification = nothing
    obj._async_dismiss_notification = nothing
    obj._async_notification = notification

    def collect(request='tick'):
        with patch.dict(sys.modules, STUBS):
            obj.hass.states.states.update(runtime.planner_states(obj._control))
        obj.payload['parallel_session'] = obj._control.get('kalibrierung_zweitsitzung', '')
        obj.payload['request'] = request
        out = run(obj.hass, obj.payload)
        return {'planung_aktiv': True, 'daten_gueltig': True, 'control_output': out,
                'plan': out['plan'], 'calibration': out['calibration']}

    async def write(command):
        assert command['restore'], 'Pending handover may only restore owned registers'
        obj.writes.append(command)
        if obj.fail_next:
            obj.fail_next = False
            return {**command, 'ok': False, 'error': 'simulated timeout'}
        set_value(obj.hass, command['entity'], command['value'])
        return {**command, 'ok': True, 'written': True}

    obj._async_write_number = write
    obj._collect_data = collect
    obj.async_request_refresh = obj._async_update_data
    return obj


def test_off_and_observe_return_both_backup_levels_and_stop_writing():
    import asyncio
    for mode in ('Aus', 'Beobachten'):
        obj = lifecycle_harness(mode)
        asyncio.run(obj._async_update_data())
        assert not obj._control['rueckgabe_ausstehend']
        assert not obj._control['sicherung'] and not obj._control['kalibrierung_sicherung']
        assert float(obj.hass.states.get(ENTITIES['A']['charge']).state) == 0
        assert float(obj.hass.states.get(ENTITIES['A']['discharge']).state) == 1500
        writes = len(obj.writes)
        asyncio.run(obj._async_update_data())
        assert len(obj.writes) == writes


def test_failed_handover_survives_restart_and_resumes_only_restoration():
    import asyncio
    obj = lifecycle_harness(failed=True)
    asyncio.run(obj._async_update_data())
    assert obj._control['rueckgabe_ausstehend'] and obj._control['sicherung']
    restarted = lifecycle_harness()
    restarted._control = copy.deepcopy(obj._control)
    restarted.hass.states = obj.hass.states
    asyncio.run(restarted._async_update_data())
    assert not restarted._control['rueckgabe_ausstehend']
    assert float(restarted.hass.states.get(ENTITIES['A']['charge']).state) == 0


def test_notification_lists_every_job_and_keeps_the_surviving_one():
    import asyncio
    obj = lifecycle_harness()
    jobs = [{'batterie': 'A', 'name': 'Venus A', 'phase': 'charge', 'phase_label': 'Kalibrierladung'},
            {'batterie': 'D', 'name': 'Venus E Keller', 'phase': 'queued', 'phase_label': 'Vorgemerkt'}]
    asyncio.run(obj._async_update_calibration_notification({'calibration': {'auftraege': jobs}}))
    body = obj._notifications[-1][-1]
    assert 'Venus A' in body and 'Venus E Keller' in body and 'Vorgemerkt' in body
    count = len(obj._notifications)
    asyncio.run(obj._async_update_calibration_notification({'calibration': {'auftraege': jobs}}))
    assert len(obj._notifications) == count
    asyncio.run(obj._async_update_calibration_notification({'calibration': {'auftraege': jobs[1:]}}))
    assert 'Venus E Keller' in obj._notifications[-1][-1] and 'Venus A' not in obj._notifications[-1][-1]


def test_day_threshold_validation_rejects_out_of_order_changes():
    import asyncio
    obj = lifecycle_harness()
    try:
        asyncio.run(obj.async_set_control('schwacher_tag', 100))
    except ValueError as err:
        assert 'aufsteigend' in str(err)
    else:
        raise AssertionError('Out of order thresholds were accepted')
    assert obj._control['schwacher_tag'] == 25


def test_sensor_attributes_publish_capacity_jobs_rest_and_remaining_time():
    from types import SimpleNamespace
    from typing import Any
    tree = ast.parse((ROOT / 'sensor.py').read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and any(
        isinstance(m, ast.FunctionDef) and m.name == 'extra_state_attributes' for m in n.body))
    method = next(m for m in cls.body if isinstance(m, ast.FunctionDef) and m.name == 'extra_state_attributes')
    scope = {'Any': Any, 'last_successful_result': lambda *args: None}
    exec(compile(ast.Module(body=[method], type_ignores=[]), 'sensor.py', 'exec'), scope)
    hass, payload = fx.scenario()
    out = run(hass, payload)
    out['plan']['restzeit_venus_a'] = {'modus': 'laden', 'restzeit_s': 1234}
    data = {'plan': out['plan'], 'calibration': out['calibration'], 'schreibzugriffe_aktiv': True}
    coordinator = SimpleNamespace(data=data, enabled_models=('A', 'E'), control={}, storage_has_packs=lambda k: k == 'A')
    entity = SimpleNamespace(coordinator=coordinator, entity_description=SimpleNamespace(key='planung'))
    attrs = scope['extra_state_attributes'].fget(entity)
    assert attrs['nennkapazitaet_venus_a_kwh'] == 4.16
    assert attrs['restzeit_venus_a']['restzeit_s'] == 1234
    assert len(attrs['kalibrierauftraege']) == 2
    entity.entity_description.key = 'kalibrierung'
    attrs = scope['extra_state_attributes'].fget(entity)
    assert len(attrs['auftraege']) == 2
    assert attrs['ruhedauer_unten_min'] == 90


def test_large_day_thresholds_are_honored_without_the_old_hidden_clamp():
    hass, payload = fx.scenario(primary_phase='idle', secondary_phase='idle')
    for key, value in [('schwacher_tag', 120), ('mittlerer_tag', 150), ('starker_tag', 180)]:
        set_value(hass, 'input_number.speicher_ladelogik_' + key, value)
    assert run(hass, payload)['plan']['tagesklasse'] == 'schwach'
