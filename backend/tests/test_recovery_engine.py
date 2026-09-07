from datetime import date, timedelta

from app.models import Athlete
from app.models.enums import ExperienceTier, WearableProvider
from app.services.program_engine import generate_training_block
from app.services.recovery_engine import (
    MAX_ADJUSTMENT,
    apply_recovery_adjustment,
    compute_and_store_score,
    record_reading,
)

BLOCK_START = date(2026, 1, 5)


def _make_athlete_with_block(db_session):
    athlete = Athlete(email="recovery-test@example.com", experience_tier=ExperienceTier.INTERMEDIATE)
    db_session.add(athlete)
    db_session.flush()
    block = generate_training_block(
        db=db_session,
        athlete=athlete,
        length_weeks=8,
        start_date=BLOCK_START,
        goal_event_date=date(2026, 3, 2),
        goal_time_seconds=5400,
    )
    return athlete, block


def test_record_reading_merges_instead_of_clobbering(db_session):
    athlete = Athlete(email="merge-test@example.com")
    db_session.add(athlete)
    db_session.flush()

    record_reading(db_session, athlete.id, date(2026, 1, 1), WearableProvider.WHOOP, hrv_ms=55, resting_hr_bpm=48)
    updated = record_reading(db_session, athlete.id, date(2026, 1, 1), WearableProvider.WHOOP, sleep_score=88)

    assert updated.hrv_ms == 55  # preserved from the first partial sync
    assert updated.resting_hr_bpm == 48
    assert updated.sleep_score == 88  # merged in from the second sync


def test_compute_score_returns_none_without_a_reading(db_session):
    athlete = Athlete(email="no-reading@example.com")
    db_session.add(athlete)
    db_session.flush()
    assert compute_and_store_score(db_session, athlete.id, date(2026, 1, 1)) is None


def test_adjustment_is_noop_without_an_active_block(db_session):
    athlete = Athlete(email="no-block@example.com")
    db_session.add(athlete)
    db_session.flush()
    record_reading(db_session, athlete.id, date(2026, 1, 1), WearableProvider.APPLE_HEALTH, hrv_ms=60, resting_hr_bpm=50, sleep_score=80)
    assert apply_recovery_adjustment(db_session, athlete.id, date(2026, 1, 1)) is None


def test_falling_recovery_deloads_the_current_week_but_not_past_the_floor(db_session):
    athlete, block = _make_athlete_with_block(db_session)
    week1 = block.weeks[0]
    planned = week1.planned_intensity

    # A stable-then-dropping run of readings so compute_trend actually reads FALLING.
    for i in range(6):
        hrv = 65 if i < 3 else 35
        rhr = 48 if i < 3 else 62
        sleep = 85 if i < 3 else 45
        day = BLOCK_START + timedelta(days=i)
        record_reading(db_session, athlete.id, day, WearableProvider.APPLE_HEALTH, hrv_ms=hrv, resting_hr_bpm=rhr, sleep_score=sleep)
        apply_recovery_adjustment(db_session, athlete.id, day)

    db_session.refresh(week1)
    floor = planned * (1 - MAX_ADJUSTMENT)
    assert week1.actual_intensity < planned
    assert week1.actual_intensity >= floor - 1e-9


def test_rising_recovery_never_pushes_intensity_past_the_original_plan(db_session):
    athlete, block = _make_athlete_with_block(db_session)
    week1 = block.weeks[0]
    planned = week1.planned_intensity

    for i in range(8):
        day = BLOCK_START + timedelta(days=i)
        record_reading(db_session, athlete.id, day, WearableProvider.APPLE_HEALTH, hrv_ms=90, resting_hr_bpm=40, sleep_score=95)
        apply_recovery_adjustment(db_session, athlete.id, day)

    db_session.refresh(week1)
    assert week1.actual_intensity <= planned + 1e-9


def test_stable_recovery_leaves_intensity_unchanged(db_session):
    athlete, block = _make_athlete_with_block(db_session)
    week1 = block.weeks[0]

    for i in range(6):
        day = BLOCK_START + timedelta(days=i)
        record_reading(db_session, athlete.id, day, WearableProvider.APPLE_HEALTH, hrv_ms=60, resting_hr_bpm=50, sleep_score=80)
        apply_recovery_adjustment(db_session, athlete.id, day)

    db_session.refresh(week1)
    assert week1.actual_intensity == week1.planned_intensity
