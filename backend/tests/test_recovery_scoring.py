from datetime import date, timedelta

from app.models.enums import RecoveryTrend
from app.services.recovery_scoring import DailyReading, compute_trend, score_day


def _baseline(days: int, hrv: float = 60, rhr: float = 50, sleep: float = 80) -> list[DailyReading]:
    return [
        DailyReading(reading_date=date(2026, 1, 1) + timedelta(days=i), hrv_ms=hrv, resting_hr_bpm=rhr, sleep_score=sleep)
        for i in range(days)
    ]


def test_at_baseline_scores_near_50():
    baseline = _baseline(28)
    today = DailyReading(reading_date=date(2026, 2, 1), hrv_ms=60, resting_hr_bpm=50, sleep_score=80)
    result = score_day(today, baseline)
    assert 45 <= result.composite_score <= 55


def test_low_hrv_and_high_resting_hr_score_below_baseline():
    baseline = _baseline(28)
    bad_day = DailyReading(reading_date=date(2026, 2, 1), hrv_ms=40, resting_hr_bpm=65, sleep_score=50)
    result = score_day(bad_day, baseline)
    assert result.composite_score < 40
    assert result.hrv_z is not None and result.hrv_z < 0
    assert result.resting_hr_z is not None and result.resting_hr_z < 0  # inverted: higher RHR = worse = negative z


def test_good_day_scores_above_baseline():
    baseline = _baseline(28)
    good_day = DailyReading(reading_date=date(2026, 2, 1), hrv_ms=80, resting_hr_bpm=42, sleep_score=95)
    result = score_day(good_day, baseline)
    assert result.composite_score > 60


def test_missing_baseline_falls_back_to_neutral_score():
    today = DailyReading(reading_date=date(2026, 2, 1), hrv_ms=60, resting_hr_bpm=50, sleep_score=80)
    result = score_day(today, [])
    assert result.composite_score == 50
    assert result.hrv_z is None


def test_trend_rising_when_recent_average_climbs():
    scores = [40, 42, 41, 55, 58, 60]
    assert compute_trend(scores) == RecoveryTrend.RISING


def test_trend_falling_when_recent_average_drops():
    scores = [60, 58, 59, 45, 42, 40]
    assert compute_trend(scores) == RecoveryTrend.FALLING


def test_trend_stable_for_small_moves():
    scores = [50, 51, 49, 50, 52, 51]
    assert compute_trend(scores) == RecoveryTrend.STABLE


def test_trend_stable_with_insufficient_history():
    assert compute_trend([50, 55]) == RecoveryTrend.STABLE
