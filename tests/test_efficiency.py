"""Selection timing and physical charging limits without a running HA server."""
from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).parents[1] / "custom_components" / "speicher_ladelogik_ae"
spec = spec_from_file_location("efficiency", ROOT / "efficiency.py")
eff = module_from_spec(spec)
spec.loader.exec_module(eff)
DAY = 1792447200
NOW = DAY + 8 * 3600


def setup():
    batteries = {
        "A": dict(lowest_soc=30, early_goal=50, target_met=False, actual_limit=1500,
                  power_fresh=True, charging_w=1000, tail=500),
        "E": dict(lowest_soc=40, early_goal=55, target_met=False, actual_limit=0,
                  power_fresh=True, charging_w=0, tail=1100),
    }
    decisions = {key: dict(active=True, limit=1500 if key == "A" else 1300,
                          released_at=NOW, reason="Tagesfreigabe") for key in batteries}
    return dict(now=NOW, day=DAY, profile="schwach", enabled=True,
                batteries=batteries, decisions=decisions, surplus=1000, export=0,
                prior={}, delay_safe=lambda key: True)


def step(parameters, old=None, offset=0, **changes):
    parameters = {**parameters, "decisions": deepcopy(parameters["decisions"]),
                  "prior": old or {}, "now": NOW + offset, **changes}
    return eff.distribute(**parameters), parameters["decisions"]


def test_1000w_uses_one_storage_and_explicitly_blocks_old_positive_register():
    p = setup()
    p["batteries"]["E"]["actual_limit"] = 1300
    state, decisions = step(p)
    assert state["primary"] == "A" and state["held"] == "E"
    assert decisions["A"]["limit"] == 1500
    assert decisions["E"]["limit"] == 0 and not decisions["E"]["active"]
    assert decisions["E"]["released_at"] is None


def test_2000w_adds_e_after_30_seconds_and_does_not_wait_for_a_to_exceed_max():
    p = setup()
    p["batteries"]["A"]["charging_w"] = 1500
    state, _ = step(p, surplus=2000, export=500)
    state, d = step(p, state, 15, surplus=2000, export=500)
    assert d["E"]["limit"] == 0
    state, d = step(p, state, 30, surplus=2000, export=500)
    assert state["mode"] == "parallel" and d["E"]["limit"] == 1300
    assert d["A"]["limit"] == 1500


def test_actual_lower_cap_not_physical_max_determines_join_threshold():
    p = setup()
    p["decisions"]["A"]["limit"] = 900
    state, _ = step(p, surplus=1150)
    state, _ = step(p, state, 15, surplus=1150)
    state, d = step(p, state, 30, surplus=1150)
    assert state["mode"] == "parallel"
    assert d["A"]["limit"] == 900


def test_cloud_spike_resets_join_timer_and_missing_cycles_do_not_count_as_stability():
    p = setup()
    state, _ = step(p, surplus=2000)
    state, _ = step(p, state, 15, surplus=1000)
    state, _ = step(p, state, 30, surplus=2000)
    state, d = step(p, state, 45, surplus=2000)
    assert d["E"]["limit"] == 0
    state, d = step(p, state, 120, surplus=2000)
    assert state["join_since"] == NOW + 120 and d["E"]["limit"] == 0


def test_parallel_survives_short_clouds_but_returns_to_single_after_three_minutes():
    p = setup()
    state = dict(day=DAY, updated_at=NOW, primary="A", mode="parallel", capacity_w=1500)
    for offset in range(0, 180, 15):
        state, d = step(p, state, offset)
        assert state["mode"] == "parallel" and d["E"]["limit"] == 1300
    state, d = step(p, state, 180)
    assert state["mode"] == "single" and d["E"]["limit"] == 0


def test_no_oscillation_when_export_disappears_because_both_absorb_pv():
    p = setup()
    state = dict(day=DAY, updated_at=NOW, primary="A", mode="parallel", capacity_w=1500)
    for offset in range(0, 600, 15):
        state, d = step(p, state, offset, surplus=2000, export=0)
        assert state["mode"] == "parallel" and state["leave_since"] is None


def test_real_export_catches_taper_and_parallel_keeps_observed_acceptance():
    p = setup()
    p["batteries"]["A"]["charging_w"] = 400
    state = None
    for offset in (0, 15, 30):
        state, d = step(p, state, offset, surplus=1000, export=600)
    assert state["mode"] == "parallel" and state["capacity_w"] == 400
    p["batteries"]["E"]["actual_limit"] = 1300
    for offset in range(45, 360, 15):
        state, _ = step(p, state, offset, surplus=1000, export=0)
        assert state["mode"] == "parallel"


def test_forecast_deadline_overrides_efficiency_pause_immediately():
    p = setup()
    state, _ = step(p)
    state, d = step(p, state, 15, delay_safe=lambda key: False)
    assert state["mode"] == "parallel" and d["E"]["limit"] == 1300
    assert "Zielfüllung" in state["reason"]


def test_primary_is_sticky_until_finished_and_lower_soc_is_selected_initially():
    p = setup()
    p["batteries"]["E"]["lowest_soc"] = 20
    state, _ = step(p)
    assert state["primary"] == "E"
    p["batteries"]["E"]["lowest_soc"] = 60
    state, _ = step(p, state, 15)
    assert state["primary"] == "E"
    p["batteries"]["E"]["target_met"] = True
    p["decisions"]["E"]["active"] = False
    state, d = step(p, state, 30)
    assert not state["active"] and d["A"]["limit"] > 0


def test_other_profiles_ineligible_storages_and_stale_measurements_are_not_overridden():
    for change in ({"profile": "stark"}, {"profile": "mittel"}, {"enabled": False}):
        p = setup()
        state, d = step(p, **change)
        assert not state["active"] and d == p["decisions"]
    p = setup()
    p["batteries"]["A"]["power_fresh"] = False
    state, d = step(p)
    assert not state["active"] and d == p["decisions"]
    p = setup()
    del p["decisions"]["E"]
    del p["batteries"]["E"]
    state, d = step(p)
    assert not state["active"] and d == p["decisions"]


def test_wechselhaft_enabled_and_new_day_does_not_reuse_old_selection():
    p = setup()
    old = dict(day=DAY - 86400, updated_at=NOW - 15, primary="E", mode="parallel")
    state, d = step(p, old, profile="wechselhaft")
    assert state["active"] and state["primary"] == "A" and d["E"]["limit"] == 0


def test_restart_keeps_mode_but_restarts_unobserved_wait_time():
    p = setup()
    old = dict(day=DAY, updated_at=NOW - 300, primary="A", mode="parallel",
               leave_since=NOW - 300, capacity_w=1500)
    state, _ = step(p, old)
    assert state["mode"] == "parallel" and state["leave_since"] == NOW
