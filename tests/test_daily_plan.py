"""Observable charging behaviour across days, cloud gaps and unequal batteries."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).parents[1] / "custom_components" / "speicher_ladelogik_ae"
spec = spec_from_file_location("daily_planner", ROOT / "charge_plan.py")
daily = module_from_spec(spec)
spec.loader.exec_module(daily)
DAY = 1790812800.0


def battery(key, soc=40, **changes):
    nominal, preferred, maximum, tail = (4.16, 1100, 1500, 500) if key == "A" else (5.12, 1300, 2500, 1100)
    return dict(nominal=nominal, preferred=preferred, maximum=maximum, tail=tail,
                soc=soc, lowest_soc=soc, goal=100, target_met=soc >= 100,
                need=nominal * (100 - soc) / 100, early_goal=0, actual_limit=0,
                **changes)


def args(**changes):
    result = dict(now=DAY + 8 * 3600, day=DAY, end=DAY + 18 * 3600,
                  midday_start=DAY + 11 * 3600, midday_end=DAY + 15 * 3600,
                  preferred_start=DAY + 11 * 3600, category="stark", peak_enabled=True,
                  forecast_ok=True, live_surplus=5000, pv_chance=True,
                  rows=[dict(t=DAY + i * 900, wh=(1500 if 28 <= i < 72 else 0)) for i in range(96)],
                  load=500, efficiency=0.9, cloud_reserve=1, reserve_factor=1.25,
                  hysteresis=0.2, batteries={"A": battery("A"), "E": battery("E")}, prior={})
    result.update(changes)
    return result


def prior_for(result, now):
    previous = {"berechnet_ts": now, "knapp": result["scarce"]}
    for key, decision in result["decisions"].items():
        previous[f"ladefreigabe_venus_{key.lower()}_seit_ts"] = decision["released_at"]
        previous[f"fahrplan_ladegrenze_stabil_venus_{key.lower()}_w"] = decision["limit"]
    return previous


def test_weak_day_starts_each_storage_at_its_preferred_cap_without_peak():
    result = daily.daily_plan(**args(category="schwach"))
    assert not result["peak_possible"]
    assert {key: d["limit"] for key, d in result["decisions"].items()} == {"A": 1100, "E": 1300}
    assert result["boosted"] == []


def test_early_goal_of_a_does_not_release_e_before_its_own_start():
    batteries = {"A": battery("A", 30), "E": battery("E", 70)}
    batteries["A"]["early_goal"] = 50
    batteries["E"]["early_goal"] = 35
    result = daily.daily_plan(**args(batteries=batteries))
    assert result["decisions"]["A"]["limit"] == 1100
    assert result["decisions"]["E"]["limit"] == 0
    assert result["decisions"]["E"]["start"] > DAY + 8 * 3600


def test_strong_day_defers_both_but_forecast_confirms_targets_in_noon_window():
    result = daily.daily_plan(**args())
    assert result["peak_possible"]
    assert all(d["limit"] == 0 for d in result["decisions"].values())
    assert result["result"]["finish"] <= DAY + 15 * 3600
    assert result["result"]["missing"] <= daily.EPS_KWH


def test_release_survives_clouds_quarter_hour_boundary_and_night():
    parameters = args(category="schwach")
    result = daily.daily_plan(**parameters)
    for hour, minute, pv in ((8, 9, 0), (8, 15, 500), (12, 0, 6000), (18, 23, 749), (23, 1, 0)):
        now = DAY + hour * 3600 + minute * 60
        parameters.update(now=now, end=max(now, DAY + 18 * 3600),
                          category="mittel", pv_chance=pv >= 200, live_surplus=pv,
                          prior=prior_for(result, parameters["now"]))
        result = daily.daily_plan(**parameters)
        assert [result["decisions"][key]["limit"] for key in ("A", "E")] == [1100, 1300]


def test_full_then_99_percent_never_escalates_even_with_a_1500w_old_register():
    for key in ("A", "E"):
        bat = battery(key, 100)
        bat["actual_limit"] = bat["maximum"]
        parameters = args(now=DAY + 17 * 3600, end=DAY + 17 * 3600 + 300,
                          batteries={key: bat}, category="schwach")
        full = daily.daily_plan(**parameters)
        assert full["decisions"][key]["limit"] == bat["maximum"]
        bat = battery(key, 99)
        bat["actual_limit"] = parameters["batteries"][key]["maximum"]
        parameters.update(batteries={key: bat}, prior=prior_for(full, parameters["now"]))
        topup = daily.daily_plan(**parameters)
        assert topup["decisions"][key]["limit"] == bat["preferred"]
        assert not topup["boosted"]


def test_pack_imbalance_cannot_be_hidden_by_an_aggregate_99_percent():
    bat = battery("A", 99)
    bat.update(lowest_soc=80, need=0.5)
    result = daily.daily_plan(**args(batteries={"A": bat}))
    assert not result["decisions"]["A"]["near_full"]


def test_pv_limited_day_does_not_request_maximum_just_because_it_is_scarce():
    rows = [dict(t=DAY + i * 900, wh=200 if 28 <= i < 72 else 0) for i in range(96)]
    result = daily.daily_plan(**args(rows=rows, category="schwach", cloud_reserve=0))
    assert result["scarce"]
    assert result["result"]["missing"] > 0
    assert not result["boosted"]
    assert [d["limit"] for d in result["decisions"].values()] == [1100, 1300]


def test_more_power_is_allowed_only_when_it_improves_the_actual_target():
    result = daily.daily_plan(**args(now=DAY + 16 * 3600, end=DAY + 18 * 3600,
                                    category="schwach", batteries={"E": battery("E", 20)}))
    assert result["boosted"] == ["E"]
    assert 1300 < result["decisions"]["E"]["limit"] <= 2500
    assert result["result"]["missing"] < result["preferred_result"]["missing"]


def test_reserve_shortfall_alone_does_not_raise_the_preferred_cap():
    result = daily.daily_plan(**args(now=DAY + 15 * 3600, end=DAY + 18 * 3600,
                                    reserve_factor=2, cloud_reserve=0, category="schwach",
                                    batteries={"E": battery("E", 40)}))
    assert result["result"]["missing"] <= daily.EPS_KWH
    assert not result["boosted"]
    assert result["decisions"]["E"]["limit"] == 1300


def test_shared_pv_is_not_counted_twice_and_cloud_reserve_is_removed_once():
    segments = daily.surplus_segments([dict(t=DAY, wh=1000)], DAY, DAY + 900, 0, 0.2)
    assert abs(segments[0][2] * 0.25 / 1000 - 0.8) < 1e-9
    batteries = {key: battery(key, 20) for key in ("A", "E")}
    needs = {key: bat["need"] for key, bat in batteries.items()}
    result = daily.simulate(segments, batteries, needs, {"A": 5000, "E": 5000},
                            {"A": DAY, "E": DAY}, 0.9, DAY + 900)
    assert abs(sum(needs.values()) - result["missing"] - 0.72) < 1e-6


def test_invalid_forecast_with_live_pv_starts_preferred_without_escalation():
    result = daily.daily_plan(**args(rows=[], forecast_ok=False))
    assert [d["limit"] for d in result["decisions"].values()] == [1100, 1300]
    assert not result["boosted"]


def test_new_day_gets_its_own_start_and_does_not_reuse_yesterdays_release():
    parameters = args()
    prior = {"berechnet_ts": DAY - 3600, "ladefreigabe_venus_a_seit_ts": DAY - 36000,
             "fahrplan_ladegrenze_stabil_venus_a_w": 1100}
    parameters["batteries"]["A"]["actual_limit"] = 1100
    result = daily.daily_plan(**{**parameters, "prior": prior})
    assert result["decisions"]["A"]["limit"] == 0
    assert result["decisions"]["A"]["released_at"] is None


def test_smaller_configured_maximum_wins_over_previous_cap():
    parameters = args(category="schwach")
    parameters["batteries"]["A"].update(maximum=900, preferred=900)
    parameters["prior"] = {"ladefreigabe_venus_a_seit_ts": DAY + 7 * 3600,
                           "fahrplan_ladegrenze_stabil_venus_a_w": 1500}
    result = daily.daily_plan(**parameters)
    assert result["decisions"]["A"]["limit"] == 900


def test_reserves_and_efficiency_can_change_scarcity_without_raising_caps():
    rows = [dict(t=DAY + i * 900, wh=275) for i in range(32, 48)]
    base = args(rows=rows, end=DAY + 12 * 3600, batteries={"A": battery("A", 60)},
                cloud_reserve=0, reserve_factor=1.25, peak_enabled=False)
    sufficient = daily.daily_plan(**base)
    assert not sufficient["scarce"]  # 2.16 kWh available for a buffered 2.08 kWh need.
    for changes in ({"cloud_reserve": 0.2}, {"reserve_factor": 1.4},
                    {"efficiency": 0.8}, {"prior": {"knapp": True}}):
        result = daily.daily_plan(**{**base, **changes})
        assert result["scarce"], changes
        assert result["decisions"]["A"]["start"] == base["now"]
        assert result["decisions"]["A"]["limit"] == 1100


def test_weak_day_keeps_the_previous_cap_even_before_first_pv():
    bat = battery("A", 50)
    bat["actual_limit"] = 1100
    result = daily.daily_plan(**args(batteries={"A": bat}, category="schwach",
                                    live_surplus=0, pv_chance=False))
    assert result["decisions"]["A"]["limit"] == 1100
    assert result["decisions"]["A"]["released_at"] is None


def test_update_adopts_an_already_active_old_plan_without_a_zero_write():
    previous = {"berechnet_ts": DAY + 7 * 3600,
                "fahrplan_slot_aktiv_venus_a": True,
                "fahrplan_ladegrenze_stabil_venus_a_w": 1100}
    result = daily.daily_plan(**args(prior=previous))
    assert result["decisions"]["A"]["limit"] == 1100
    assert result["decisions"]["A"]["released_at"] == previous["berechnet_ts"]
    assert result["decisions"]["E"]["limit"] == 0


def test_forecast_house_deficit_is_shared_and_must_be_recharged():
    batteries = {key: battery(key, 100) for key in ("A", "E")}
    needs = {key: 0 for key in batteries}
    caps = {key: bat["preferred"] for key, bat in batteries.items()}
    starts = {key: DAY for key in batteries}
    # 0.5 kWh of house demand cannot disappear from the forecast simply because
    # both batteries are already full at the start of the simulation.
    result = daily.simulate([[DAY, DAY + 1800, -1000]], batteries, needs, caps, starts, 0.9, DAY + 1800)
    assert abs(result["missing"] - 0.5) < 1e-6
    assert result["finish"] is None
    recovered = daily.simulate([[DAY, DAY + 1800, -1000], [DAY + 1800, DAY + 5400, 4000]],
                               batteries, needs, caps, starts, 0.9, DAY + 5400)
    assert recovered["missing"] <= daily.EPS_KWH
    assert recovered["finish"] > DAY + 1800
    # An empty battery cannot discharge below its lower device boundary.
    empty = {"E": battery("E", 12)}
    exhausted = daily.simulate([[DAY, DAY + 1800, -1000]], empty,
                               {"E": empty["E"]["need"]}, {"E": 1300}, {"E": DAY}, 0.9, DAY + 1800)
    assert exhausted["missing"] == empty["E"]["need"]
