from datetime import date

from app.models import Athlete
from app.models.enums import ExperienceTier
from app.services.heart_rate import estimate_max_hr
from app.services.program_engine import (
    LOADABLE_STATIONS,
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
    assert weeks_by_number[1].workouts[2].title == "Run & Row Training"

    assert weeks_by_number[6].phase == "build"
    assert weeks_by_number[6].workouts[2].title == "Threshold Run"

    assert weeks_by_number[7].phase == "peak"
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
