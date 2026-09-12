from app.models import Athlete
from app.services.pace import pace_for_zone, predict_equivalent_time, resolve_pace_profile


def test_riegel_prediction_matches_known_real_world_equivalent():
    # A 20:00 5K (1200s) predicts to roughly 41:30-42:00 for 10K in practice.
    predicted_10k = predict_equivalent_time(1200, 5000, 10000)
    assert 2480 <= predicted_10k <= 2560


def test_riegel_is_symmetric_within_rounding():
    predicted_10k = predict_equivalent_time(1200, 5000, 10000)
    predicted_5k_back = predict_equivalent_time(predicted_10k, 10000, 5000)
    assert abs(predicted_5k_back - 1200) < 1.0


def test_profile_none_when_athlete_has_neither_pb():
    athlete = Athlete(email="a@example.com", predicted_5k_seconds=None, current_10k_seconds=None)
    assert resolve_pace_profile(athlete) is None


def test_profile_cross_predicts_missing_pb_from_the_one_thats_set():
    athlete = Athlete(email="a@example.com", predicted_5k_seconds=1200, current_10k_seconds=None)
    profile = resolve_pace_profile(athlete)
    assert profile is not None
    assert profile.five_k_pace_sec_per_km == 1200 / 5
    assert profile.ten_k_pace_sec_per_km > profile.five_k_pace_sec_per_km


def test_profile_uses_both_pbs_directly_when_both_are_set():
    athlete = Athlete(email="a@example.com", predicted_5k_seconds=1200, current_10k_seconds=2520)
    profile = resolve_pace_profile(athlete)
    assert profile.five_k_pace_sec_per_km == 1200 / 5
    assert profile.ten_k_pace_sec_per_km == 2520 / 10


def test_pace_zones_are_ordered_fastest_to_slowest():
    athlete = Athlete(email="a@example.com", predicted_5k_seconds=1200, current_10k_seconds=2520)
    profile = resolve_pace_profile(athlete)
    interval = pace_for_zone(profile, "interval")
    threshold = pace_for_zone(profile, "threshold")
    easy = pace_for_zone(profile, "easy")
    long_run = pace_for_zone(profile, "long_run")
    assert interval < threshold < easy < long_run


def test_unknown_zone_returns_none():
    athlete = Athlete(email="a@example.com", predicted_5k_seconds=1200)
    profile = resolve_pace_profile(athlete)
    assert pace_for_zone(profile, "sprint") is None
