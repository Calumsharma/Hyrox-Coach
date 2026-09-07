from app.models import Athlete
from app.models.enums import HeartRateZone
from app.services.heart_rate import estimate_max_hr, resolve_max_hr, zone_target


def test_tanaka_formula():
    assert estimate_max_hr(30) == 187  # 208 - 0.7*30 = 187.0
    assert estimate_max_hr(40) == 180  # 208 - 0.7*40 = 180.0


def test_tested_max_hr_takes_priority_over_estimate():
    athlete = Athlete(email="a@example.com", age=30, tested_max_hr=195)
    assert resolve_max_hr(athlete) == 195


def test_falls_back_to_tanaka_when_untested():
    athlete = Athlete(email="a@example.com", age=30, tested_max_hr=None)
    assert resolve_max_hr(athlete) == estimate_max_hr(30)


def test_missing_age_and_test_returns_none():
    athlete = Athlete(email="a@example.com", age=None, tested_max_hr=None)
    assert resolve_max_hr(athlete) is None


def test_zone_target_computes_bpm_range():
    athlete = Athlete(email="a@example.com", age=30, tested_max_hr=190)
    target = zone_target(athlete, HeartRateZone.Z2_AEROBIC_BASE)
    assert target.low_bpm == round(190 * 0.60)
    assert target.high_bpm == round(190 * 0.70)


def test_zone_target_without_resolvable_max_hr_still_returns_percentages():
    athlete = Athlete(email="a@example.com", age=None, tested_max_hr=None)
    target = zone_target(athlete, HeartRateZone.Z4_THRESHOLD)
    assert target.low_bpm is None
    assert target.low_pct == 0.80 and target.high_pct == 0.90


def test_zone_order_is_ascending_and_non_overlapping():
    zones = [HeartRateZone.Z1_RECOVERY, HeartRateZone.Z2_AEROBIC_BASE, HeartRateZone.Z3_TEMPO, HeartRateZone.Z4_THRESHOLD, HeartRateZone.Z5_ANAEROBIC]
    athlete = Athlete(email="a@example.com", age=30, tested_max_hr=200)
    targets = [zone_target(athlete, z) for z in zones]
    for earlier, later in zip(targets, targets[1:]):
        assert earlier.high_bpm <= later.low_bpm
