from app.models.enums import ExperienceTier
from app.services.experience_tier import suggest_tier_from_inputs


def test_advanced_by_time_alone_even_with_few_races():
    assert suggest_tier_from_inputs(best_solo_time_seconds=70 * 60, race_count=1) == ExperienceTier.ADVANCED


def test_advanced_by_race_count_alone_even_with_slow_time():
    assert suggest_tier_from_inputs(best_solo_time_seconds=100 * 60, race_count=6) == ExperienceTier.ADVANCED


def test_intermediate_needs_both_time_and_race_count():
    assert suggest_tier_from_inputs(best_solo_time_seconds=85 * 60, race_count=4) == ExperienceTier.INTERMEDIATE


def test_fast_time_but_too_few_races_is_not_intermediate_boundary():
    # 80 min alone with only 2 races doesn't hit Advanced (needs <=75 or >=5 races)
    # or Intermediate (needs 3-5 races) — falls through to Beginner.
    assert suggest_tier_from_inputs(best_solo_time_seconds=80 * 60, race_count=2) == ExperienceTier.BEGINNER


def test_slow_time_with_few_races_is_beginner():
    assert suggest_tier_from_inputs(best_solo_time_seconds=110 * 60, race_count=1) == ExperienceTier.BEGINNER


def test_no_race_history_defaults_beginner():
    assert suggest_tier_from_inputs(best_solo_time_seconds=None, race_count=0) == ExperienceTier.BEGINNER


def test_boundary_values_are_inclusive():
    assert suggest_tier_from_inputs(best_solo_time_seconds=75 * 60, race_count=0) == ExperienceTier.ADVANCED
    assert suggest_tier_from_inputs(best_solo_time_seconds=90 * 60, race_count=3) == ExperienceTier.INTERMEDIATE
