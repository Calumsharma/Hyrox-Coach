from datetime import date

from app.models import AccessoryMovement, Athlete, StationReference
from app.models.enums import Division, ExperienceTier, StationSlug
from app.services.heart_rate import estimate_max_hr
from app.services.pace import resolve_pace_profile
from app.services.program_engine import (
    LOADABLE_STATIONS,
    TIER_OVERLOAD_MULTIPLIER,
    _choose_focus_stations,
    generate_training_block,
    suggest_deload_weeks,
    suggest_taper_weeks,
)


def test_suggested_schedule_matches_reference_8_week_block():
    assert suggest_deload_weeks(8) == [4]
    assert suggest_taper_weeks(8) == [8]


def test_weak_station_appears_far_more_often_than_round_robin_baseline():
    weaknesses = ["sled_pull"]
    weeks = 15  # enough load weeks to make round-robin baseline (1/5) clearly distinguishable
    appearances = sum(
        1 for i in range(weeks) if "sled_pull" in _choose_focus_stations(i, weaknesses)
    )
    round_robin_baseline = weeks / len(LOADABLE_STATIONS)
    assert appearances > round_robin_baseline * 2
    assert appearances == weeks  # in this design the weakness appears every single load week


def test_no_weakness_falls_back_to_plain_round_robin():
    stations_seen = {tuple(_choose_focus_stations(i, [])) for i in range(len(LOADABLE_STATIONS))}
    assert len(stations_seen) == len(LOADABLE_STATIONS)


def test_generated_block_uses_athletes_tier(db_session):
    athlete = Athlete(email="tier-test@example.com", experience_tier=ExperienceTier.ADVANCED)
    db_session.add(athlete)
    db_session.flush()

    block = generate_training_block(
        db=db_session,
        athlete=athlete,
        length_weeks=8,
        start_date=date(2026, 1, 1),
        goal_event_date=date(2026, 2, 26),
        goal_time_seconds=4200,
    )

    strength_block = block.weeks[0].workouts[0].prescription["blocks"][0]
    assert strength_block["reps"] == 5  # Advanced/Intermediate/Beginner load-week strength is identical (4x5)

    long_run = block.weeks[0].workouts[6].prescription["blocks"][0]
    assert long_run["duration_min"] == "55-60"  # Advanced long-run range


def test_race_week_is_only_the_final_week(db_session):
    athlete = Athlete(email="race-week-test@example.com", experience_tier=ExperienceTier.BEGINNER)
    db_session.add(athlete)
    db_session.flush()

    block = generate_training_block(
        db=db_session,
        athlete=athlete,
        length_weeks=8,
        start_date=date(2026, 1, 1),
        goal_event_date=date(2026, 2, 26),
        goal_time_seconds=5400,
    )

    race_day_weeks = [
        w.week_number for w in block.weeks
        if any(wo.workout_type == "race_day" for wo in w.workouts)
    ]
    assert race_day_weeks == [8]


def test_threshold_run_replaces_intervals_for_advanced_during_build_and_peak_only(db_session):
    athlete = Athlete(email="threshold-test@example.com", age=30, experience_tier=ExperienceTier.ADVANCED)
    db_session.add(athlete)
    db_session.flush()

    block = generate_training_block(
        db=db_session, athlete=athlete, length_weeks=8,
        start_date=date(2026, 1, 1), goal_event_date=date(2026, 2, 26), goal_time_seconds=4200,
    )
    weeks_by_number = {w.week_number: w for w in block.weeks}

    assert weeks_by_number[1].phase == "base"
    assert weeks_by_number[1].workouts[2].title == "The Grind"

    # Weeks 5-7 are the 4th-6th *load* weeks (week 4 is deload, week 8 is taper) — the
    # base->build->peak progression runs over just the 6 real load weeks, so it's compressed
    # relative to raw calendar position. Both land in build/peak, which is what matters for
    # the threshold-run swap.
    assert weeks_by_number[6].phase in ("build", "peak")
    assert weeks_by_number[6].workouts[2].title == "Threshold Run"

    assert weeks_by_number[7].phase in ("build", "peak")
    assert weeks_by_number[7].workouts[2].title == "Threshold Run"


def test_beginners_never_get_the_threshold_run(db_session):
    athlete = Athlete(email="beginner-threshold-test@example.com", age=30, experience_tier=ExperienceTier.BEGINNER)
    db_session.add(athlete)
    db_session.flush()

    block = generate_training_block(
        db=db_session, athlete=athlete, length_weeks=8,
        start_date=date(2026, 1, 1), goal_event_date=date(2026, 2, 26), goal_time_seconds=4200,
    )
    titles = {w.week_number: w.workouts[2].title for w in block.weeks}
    assert "Threshold Run" not in titles.values()


def test_deload_week_does_not_skip_the_build_phase(db_session):
    """Regression test: a 6-week block used to go base,base,base,deload,PEAK,taper — jumping
    straight from a deload into peak intensity with no build ramp, because the old curve was
    indexed by raw calendar week rather than by load week. It should now always pass through
    build before peak, regardless of where the deload week falls."""
    athlete = Athlete(email="deload-gap-test@example.com", age=30, experience_tier=ExperienceTier.ADVANCED)
    db_session.add(athlete)
    db_session.flush()

    block = generate_training_block(
        db=db_session, athlete=athlete, length_weeks=6,
        start_date=date(2026, 1, 1), goal_event_date=date(2026, 2, 12), goal_time_seconds=4200,
    )
    load_phases_in_order = [w.phase for w in block.weeks if w.phase not in ("deload", "taper")]
    assert "build" in load_phases_in_order
    assert load_phases_in_order.index("build") < load_phases_in_order.index("peak")


def test_every_load_week_phase_matches_its_actual_workout_content(db_session):
    """Regression test: a week's stored phase label must never claim "taper" while actually
    containing full-intensity _load_week content (or vice versa) — this happened on longer
    blocks when the curve's own internal taper band (progress >= 90%) landed on a week that
    wasn't in the block's explicit taper_week_numbers."""
    athlete = Athlete(email="phase-consistency-test@example.com", age=30, experience_tier=ExperienceTier.ADVANCED)
    db_session.add(athlete)
    db_session.flush()

    block = generate_training_block(
        db=db_session, athlete=athlete, length_weeks=12,
        start_date=date(2026, 1, 1), goal_event_date=date(2026, 3, 26), goal_time_seconds=4200,
    )
    for week in block.weeks:
        if week.week_number in block.taper_week_numbers:
            assert week.phase == "taper"
        elif week.week_number in block.deload_week_numbers:
            assert week.phase == "deload"
        else:
            assert week.phase in ("base", "build", "peak")


def test_zone_2_blocks_carry_the_athletes_own_hr_target(db_session):
    athlete = Athlete(email="hr-target-test@example.com", age=30, experience_tier=ExperienceTier.BEGINNER)
    db_session.add(athlete)
    db_session.flush()

    block = generate_training_block(
        db=db_session, athlete=athlete, length_weeks=8,
        start_date=date(2026, 1, 1), goal_event_date=date(2026, 2, 26), goal_time_seconds=4200,
    )
    long_run_block = block.weeks[0].workouts[6].prescription["blocks"][0]
    max_hr = estimate_max_hr(30)
    assert long_run_block["target_hr_bpm"] == [round(max_hr * 0.60), round(max_hr * 0.70)]


def test_pace_targets_present_when_athlete_has_pb_data(db_session):
    athlete = Athlete(
        email="pace-test@example.com", experience_tier=ExperienceTier.BEGINNER,
        predicted_5k_seconds=1200, current_10k_seconds=2520,
    )
    db_session.add(athlete)
    db_session.flush()

    block = generate_training_block(
        db=db_session, athlete=athlete, length_weeks=8,
        start_date=date(2026, 1, 1), goal_event_date=date(2026, 2, 26), goal_time_seconds=4200,
    )
    easy_run_block = block.weeks[0].workouts[1].prescription["blocks"][0]
    profile = resolve_pace_profile(athlete)
    assert easy_run_block["target_pace_per_km_sec"] == round(profile.easy_pace_sec_per_km)


def test_pace_targets_absent_and_no_crash_without_pb_data(db_session):
    athlete = Athlete(email="no-pace-test@example.com", experience_tier=ExperienceTier.BEGINNER)
    db_session.add(athlete)
    db_session.flush()

    block = generate_training_block(
        db=db_session, athlete=athlete, length_weeks=8,
        start_date=date(2026, 1, 1), goal_event_date=date(2026, 2, 26), goal_time_seconds=4200,
    )
    easy_run_block = block.weeks[0].workouts[1].prescription["blocks"][0]
    assert "target_pace_per_km_sec" not in easy_run_block


def test_overload_kg_uses_real_division_race_weight_and_tier_multiplier(db_session):
    db_session.add(StationReference(
        slug=StationSlug.SLED_PUSH, order=2, name="Sled Push", distance_or_reps="50 m",
        primary_demand="leg strength / posterior chain",
        division_loads={"open_men": {"load_kg": 152}},
    ))
    athlete = Athlete(email="overload-test@example.com", experience_tier=ExperienceTier.ADVANCED, division=Division.OPEN_MEN)
    db_session.add(athlete)
    db_session.flush()

    block = generate_training_block(
        db=db_session, athlete=athlete, length_weeks=8,
        start_date=date(2026, 1, 1), goal_event_date=date(2026, 2, 26), goal_time_seconds=4200,
    )
    station_workout = block.weeks[0].workouts[3]  # week 1's rotation always lands on sled_push (index 0)
    sled_push_block = next(b for b in station_workout.prescription["blocks"] if b["movement"] == "sled_push")
    assert sled_push_block["overload_kg"] == round(152 * TIER_OVERLOAD_MULTIPLIER[ExperienceTier.ADVANCED], 1)


def test_overload_kg_absent_when_division_not_set(db_session):
    db_session.add(StationReference(
        slug=StationSlug.SLED_PUSH, order=2, name="Sled Push", distance_or_reps="50 m",
        primary_demand="leg strength / posterior chain",
        division_loads={"open_men": {"load_kg": 152}},
    ))
    athlete = Athlete(email="no-division-test@example.com", experience_tier=ExperienceTier.ADVANCED)
    db_session.add(athlete)
    db_session.flush()

    block = generate_training_block(
        db=db_session, athlete=athlete, length_weeks=8,
        start_date=date(2026, 1, 1), goal_event_date=date(2026, 2, 26), goal_time_seconds=4200,
    )
    station_workout = block.weeks[0].workouts[3]
    sled_push_block = next(b for b in station_workout.prescription["blocks"] if b["movement"] == "sled_push")
    assert "overload_kg" not in sled_push_block


def test_weakness_with_no_matching_fixed_lift_swaps_in_the_real_accessory_movement(db_session):
    db_session.add(AccessoryMovement(
        id="overhead_press", name="Overhead Press", category="strength",
        addresses_stations=["wall_balls", "skierg"], notes="5/3/1 main lift",
    ))
    athlete = Athlete(
        email="weakness-swap-test@example.com", experience_tier=ExperienceTier.ADVANCED,
        self_reported_weak_stations=["wall_balls"],
    )
    db_session.add(athlete)
    db_session.flush()

    block = generate_training_block(
        db=db_session, athlete=athlete, length_weeks=8,
        start_date=date(2026, 1, 1), goal_event_date=date(2026, 2, 26), goal_time_seconds=4200,
    )
    strength_blocks = block.weeks[0].workouts[0].prescription["blocks"]
    assert strength_blocks[0]["reps"] == 5  # index 0 (front squat) untouched by any swap
    assert strength_blocks[2]["movement"] == "overhead_press"  # swapped in for the wall_balls weakness


def test_weakness_matching_an_existing_lift_flags_it_as_priority_instead_of_swapping(db_session):
    db_session.add(AccessoryMovement(
        id="deadlift", name="Deadlift", category="strength",
        addresses_stations=["sled_pull", "farmers_carry"], notes="5/3/1 main lift",
    ))
    athlete = Athlete(
        email="weakness-flag-test@example.com", experience_tier=ExperienceTier.ADVANCED,
        self_reported_weak_stations=["sled_pull"],
    )
    db_session.add(athlete)
    db_session.flush()

    block = generate_training_block(
        db=db_session, athlete=athlete, length_weeks=8,
        start_date=date(2026, 1, 1), goal_event_date=date(2026, 2, 26), goal_time_seconds=4200,
    )
    strength_blocks = block.weeks[0].workouts[0].prescription["blocks"]
    assert strength_blocks[1]["movement"] == "hex_bar_deadlift"  # same lift, not swapped
    assert "Priority lift" in strength_blocks[1].get("note", "")
