"""Wires the pure scoring math in `recovery_scoring.py` to the database and to actual
`TrainingWeek.actual_intensity` adjustments.

This is deliberately the single place wearable data (via Terra/Spike once that's wired up,
or manual/dev entry in the meantime) turns into a program change — record a reading, score
it, adjust the current week. Nothing else should touch `actual_intensity` directly.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import RecoveryReading, RecoveryScore, TrainingBlock, TrainingWeek
from app.models.enums import RecoveryTrend, WearableProvider
from app.services.recovery_scoring import DailyReading, compute_trend, score_day

BASELINE_WINDOW_DAYS = 28
TREND_LOOKBACK_DAYS = 6

# Bounded relative to the week's *original* plan — recovery can slow the block down or bring
# it back up, but never past what was planned (see "Recovery-Driven Adjustment Logic" in the plan).
MAX_ADJUSTMENT = 0.15
ADJUSTMENT_STEP = 0.05


def record_reading(
    db: Session,
    athlete_id: str,
    reading_date: date,
    source: WearableProvider,
    hrv_ms: Optional[float] = None,
    resting_hr_bpm: Optional[float] = None,
    sleep_score: Optional[float] = None,
    vo2_max: Optional[float] = None,
) -> RecoveryReading:
    """One reading per athlete per day. Merges new non-null fields into an existing reading
    rather than overwriting it blindly, since a day's data can arrive from more than one sync."""

    existing = (
        db.query(RecoveryReading)
        .filter(RecoveryReading.athlete_id == athlete_id, RecoveryReading.reading_date == reading_date)
        .first()
    )
    if existing:
        if hrv_ms is not None:
            existing.hrv_ms = hrv_ms
        if resting_hr_bpm is not None:
            existing.resting_hr_bpm = resting_hr_bpm
        if sleep_score is not None:
            existing.sleep_score = sleep_score
        # Program Engine v5 Milestone 2: record VO2max field-level provenance only when the
        # value actually changes (or is set for the first time) — never on every merge, which
        # is what previously made the bare `source` column an unreliable stand-in for "who
        # actually supplied this VO2max value" (an independent audit flagged this; see the
        # Milestone 2 v2.2 plan, §D2). An unchanged resync of the same value is not a new
        # revision and must not bump `vo2_max_updated_at`.
        vo2max_changed = vo2_max is not None and vo2_max != existing.vo2_max
        if vo2_max is not None:
            existing.vo2_max = vo2_max
        if vo2max_changed:
            existing.vo2_max_source = source
            existing.vo2_max_recorded_at = datetime.combine(reading_date, time.min)
            existing.vo2_max_updated_at = datetime.utcnow()
        existing.source = source
        reading = existing
    else:
        reading = RecoveryReading(
            athlete_id=athlete_id,
            reading_date=reading_date,
            source=source,
            hrv_ms=hrv_ms,
            resting_hr_bpm=resting_hr_bpm,
            sleep_score=sleep_score,
            vo2_max=vo2_max,
        )
        if vo2_max is not None:
            reading.vo2_max_source = source
            reading.vo2_max_recorded_at = datetime.combine(reading_date, time.min)
            reading.vo2_max_updated_at = datetime.utcnow()
        db.add(reading)

    db.commit()
    db.refresh(reading)
    return reading


def _to_daily_reading(reading: RecoveryReading) -> DailyReading:
    return DailyReading(
        reading_date=reading.reading_date,
        hrv_ms=reading.hrv_ms,
        resting_hr_bpm=reading.resting_hr_bpm,
        sleep_score=reading.sleep_score,
    )


def compute_and_store_score(db: Session, athlete_id: str, target_date: date) -> Optional[RecoveryScore]:
    """Scores `target_date` against the athlete's preceding baseline. Returns None if there's
    no reading for that day yet — can't score what hasn't arrived."""

    target_reading = (
        db.query(RecoveryReading)
        .filter(RecoveryReading.athlete_id == athlete_id, RecoveryReading.reading_date == target_date)
        .first()
    )
    if target_reading is None:
        return None

    baseline_readings = (
        db.query(RecoveryReading)
        .filter(
            RecoveryReading.athlete_id == athlete_id,
            RecoveryReading.reading_date >= target_date - timedelta(days=BASELINE_WINDOW_DAYS),
            RecoveryReading.reading_date < target_date,
        )
        .all()
    )

    result = score_day(
        _to_daily_reading(target_reading),
        [_to_daily_reading(r) for r in baseline_readings],
    )

    recent_scores = (
        db.query(RecoveryScore)
        .filter(
            RecoveryScore.athlete_id == athlete_id,
            RecoveryScore.score_date >= target_date - timedelta(days=TREND_LOOKBACK_DAYS),
            RecoveryScore.score_date < target_date,
        )
        .order_by(RecoveryScore.score_date)
        .all()
    )
    trend = compute_trend([s.composite_score for s in recent_scores] + [result.composite_score])

    existing = (
        db.query(RecoveryScore)
        .filter(RecoveryScore.athlete_id == athlete_id, RecoveryScore.score_date == target_date)
        .first()
    )
    if existing is None:
        existing = RecoveryScore(athlete_id=athlete_id, score_date=target_date)
        db.add(existing)

    existing.composite_score = result.composite_score
    existing.hrv_z = result.hrv_z
    existing.resting_hr_z = result.resting_hr_z
    existing.sleep_z = result.sleep_z
    existing.trend = trend

    db.commit()
    db.refresh(existing)
    return existing


def _find_current_week(db: Session, athlete_id: str, on_date: date) -> Optional[TrainingWeek]:
    block = (
        db.query(TrainingBlock)
        .filter(TrainingBlock.athlete_id == athlete_id)
        .order_by(TrainingBlock.start_date.desc())
        .first()
    )
    if block is None:
        return None

    days_elapsed = (on_date - block.start_date).days
    if days_elapsed < 0:
        return None
    week_number = days_elapsed // 7 + 1
    return next((w for w in block.weeks if w.week_number == week_number), None)


def apply_recovery_adjustment(db: Session, athlete_id: str, on_date: Optional[date] = None) -> Optional[TrainingWeek]:
    """The core mechanism: a falling recovery trend nudges the current week's actual_intensity
    down (bounded at 15% below plan) — a deload, not a skip. A rising trend nudges it back
    toward (never past) the week's original planned_intensity. A stable trend leaves it alone."""

    on_date = on_date or date.today()
    score = compute_and_store_score(db, athlete_id, on_date)
    if score is None:
        return None

    week = _find_current_week(db, athlete_id, on_date)
    if week is None:
        return None

    floor = week.planned_intensity * (1 - MAX_ADJUSTMENT)
    ceiling = week.planned_intensity

    if score.trend == RecoveryTrend.FALLING:
        week.actual_intensity = max(floor, week.actual_intensity - ADJUSTMENT_STEP)
    elif score.trend == RecoveryTrend.RISING:
        week.actual_intensity = min(ceiling, week.actual_intensity + ADJUSTMENT_STEP)

    db.commit()
    db.refresh(week)
    return week
