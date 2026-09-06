"""Pure scoring logic for the recovery engine — no DB access, so it's cheap to test exhaustively.

A day's composite recovery score is a 0-100 value centered on 50, built by z-scoring that
day's HRV / resting HR / sleep against the athlete's OWN rolling baseline (never a population
norm — "low HRV" only means something relative to that person's usual range). Trend is a
simple two-window comparison: is the last few days' average recovery rising, falling, or
holding relative to the few days before that.
"""

import statistics
from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.models.enums import RecoveryTrend

TREND_WINDOW_DAYS = 3
TREND_THRESHOLD = 3.0  # composite-score points; smaller moves are treated as noise, not a trend


@dataclass
class DailyReading:
    reading_date: date
    hrv_ms: Optional[float] = None
    resting_hr_bpm: Optional[float] = None
    sleep_score: Optional[float] = None


@dataclass
class ScoreResult:
    composite_score: float
    hrv_z: Optional[float]
    resting_hr_z: Optional[float]
    sleep_z: Optional[float]


def _zscore(value: Optional[float], baseline: list[float]) -> Optional[float]:
    if value is None or len(baseline) < 2:
        return None
    mean = statistics.mean(baseline)
    stdev = statistics.pstdev(baseline) or 1.0
    return (value - mean) / stdev


def score_day(target: DailyReading, baseline: list[DailyReading]) -> ScoreResult:
    """Scores `target` against `baseline` (typically the preceding ~28 days, excluding target)."""

    hrv_z = _zscore(target.hrv_ms, [r.hrv_ms for r in baseline if r.hrv_ms is not None])
    # Lower resting HR is better, so this is inverted relative to HRV/sleep.
    resting_hr_z = _zscore(target.resting_hr_bpm, [r.resting_hr_bpm for r in baseline if r.resting_hr_bpm is not None])
    if resting_hr_z is not None:
        resting_hr_z = -resting_hr_z
    sleep_z = _zscore(target.sleep_score, [r.sleep_score for r in baseline if r.sleep_score is not None])

    components = [z for z in (hrv_z, resting_hr_z, sleep_z) if z is not None]
    composite_z = statistics.mean(components) if components else 0.0
    composite_score = max(0.0, min(100.0, 50 + composite_z * 15))

    return ScoreResult(composite_score=composite_score, hrv_z=hrv_z, resting_hr_z=resting_hr_z, sleep_z=sleep_z)


def compute_trend(recent_scores_oldest_first: list[float]) -> RecoveryTrend:
    """Compares the most recent window of composite scores against the window before it."""

    window = TREND_WINDOW_DAYS
    if len(recent_scores_oldest_first) < window * 2:
        return RecoveryTrend.STABLE

    older = recent_scores_oldest_first[-window * 2:-window]
    newer = recent_scores_oldest_first[-window:]
    delta = statistics.mean(newer) - statistics.mean(older)

    if delta >= TREND_THRESHOLD:
        return RecoveryTrend.RISING
    if delta <= -TREND_THRESHOLD:
        return RecoveryTrend.FALLING
    return RecoveryTrend.STABLE
