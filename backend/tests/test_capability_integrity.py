"""Referential-integrity and CHECK-constraint tests for the capability foundation —
Program Engine v5 Milestone 1B. Composite foreign keys must make cross-athlete/cross-metric
citations physically unrepresentable in the database, not just checked in code; every CHECK
constraint here is exercised in both directions.
"""

import subprocess
from datetime import date, datetime
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    Athlete,
    BenchmarkDefinition,
    BenchmarkResult,
    CapabilityAssessment,
    CapabilityBand,
    CapabilityBandPolicy,
    CapabilityConfidencePolicy,
    CapabilityConfidenceRule,
    CapabilityDefinition,
    CapabilityGap,
    CapabilityMetric,
    CapabilityScore,
    CapabilityScoreAssessment,
    PastHyroxResult,
    RecoveryReading,
    TrainingBlock,
    TrainingWeek,
    Workout,
)
from app.models.immutability import ImmutableRecordError

REPO_ROOT = Path(__file__).resolve().parent.parent


def _athlete(db_session, email):
    athlete = Athlete(email=email)
    db_session.add(athlete)
    db_session.commit()
    return athlete


def _metric(db_session, metric_id="threshold_pace_riegel_sec_per_km", capability_id="threshold_race_pace", station=None):
    if db_session.get(CapabilityDefinition, capability_id) is None:
        db_session.add(CapabilityDefinition(id=capability_id, name=capability_id, description="", measurement_hint=""))
    metric = CapabilityMetric(
        id=metric_id, capability_id=capability_id, station=station, unit="sec_per_km",
        higher_is_better=False, evidence_class="coach_derived", description="",
    )
    db_session.add(metric)
    db_session.commit()
    return metric


def _assessment(db_session, athlete, metric, **overrides):
    defaults = dict(
        athlete_id=athlete.id, metric_id=metric.id, raw_value=300.0,
        assessment_type="self_report", recorded_at=datetime(2026, 9, 1), evidence_class="coach_derived",
    )
    defaults.update(overrides)
    assessment = CapabilityAssessment(**defaults)
    db_session.add(assessment)
    db_session.commit()
    return assessment


def _score(db_session, athlete, metric):
    score = CapabilityScore(
        athlete_id=athlete.id, metric_id=metric.id, value=300.0,
        computation_method="test_v1", evidence_class="coach_derived", computed_at=datetime(2026, 9, 1),
    )
    db_session.add(score)
    db_session.commit()
    return score


# ============================================================
# Composite-FK athlete-ownership: CapabilityAssessment -> BenchmarkResult/RecoveryReading/PastHyroxResult
# ============================================================

def test_assessment_benchmark_result_cross_athlete_is_rejected(db_session):
    athlete1 = _athlete(db_session, "int-a1@example.com")
    athlete2 = _athlete(db_session, "int-a2@example.com")
    metric = _metric(db_session)

    definition = BenchmarkDefinition(name="5K Time Trial", protocol_description="", unit="sec", evidence_class="coach_derived")
    db_session.add(definition)
    db_session.commit()
    benchmark_result = BenchmarkResult(
        athlete_id=athlete2.id, benchmark_id=definition.id, completed_at=datetime(2026, 9, 1), raw_value=1200.0, context={},
    )
    db_session.add(benchmark_result)
    db_session.commit()

    db_session.add(CapabilityAssessment(
        athlete_id=athlete1.id, metric_id=metric.id, raw_value=300.0, derivation_method="riegel_threshold_pace_v1",
        assessment_type="benchmark_result", benchmark_result_id=benchmark_result.id,
        recorded_at=datetime(2026, 9, 1), evidence_class="coach_derived",
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_assessment_recovery_reading_cross_athlete_is_rejected(db_session):
    athlete1 = _athlete(db_session, "int-b1@example.com")
    athlete2 = _athlete(db_session, "int-b2@example.com")
    metric = _metric(db_session, metric_id="vo2max_wearable_ml_kg_min", capability_id="aerobic_capacity")

    reading = RecoveryReading(athlete_id=athlete2.id, reading_date=date(2026, 9, 1), source="apple_health", vo2_max=52.0)
    db_session.add(reading)
    db_session.commit()

    db_session.add(CapabilityAssessment(
        athlete_id=athlete1.id, metric_id=metric.id, raw_value=52.0,
        assessment_type="wearable_derived", recovery_reading_id=reading.id,
        recorded_at=datetime(2026, 9, 1), evidence_class="research_supported",
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_assessment_past_hyrox_result_cross_athlete_is_rejected(db_session):
    athlete1 = _athlete(db_session, "int-c1@example.com")
    athlete2 = _athlete(db_session, "int-c2@example.com")
    metric = _metric(db_session, metric_id="post_station_split_penalty_sec_per_km", capability_id="compromised_running")

    result = PastHyroxResult(
        athlete_id=athlete2.id, event_date=date(2026, 6, 1), division="open_men",
        total_time_seconds=5400, station_splits_seconds={},
    )
    db_session.add(result)
    db_session.commit()

    db_session.add(CapabilityAssessment(
        athlete_id=athlete1.id, metric_id=metric.id, raw_value=12.0, derivation_method="post_station_split_penalty_v1",
        assessment_type="race_result", past_hyrox_result_id=result.id,
        recorded_at=datetime(2026, 9, 1), evidence_class="coach_derived",
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_assessment_source_ownership_same_athlete_is_accepted(db_session):
    athlete = _athlete(db_session, "int-d1@example.com")
    metric = _metric(db_session, metric_id="post_station_split_penalty_sec_per_km", capability_id="compromised_running")

    result = PastHyroxResult(
        athlete_id=athlete.id, event_date=date(2026, 6, 1), division="open_men",
        total_time_seconds=5400, station_splits_seconds={},
    )
    db_session.add(result)
    db_session.commit()

    db_session.add(CapabilityAssessment(
        athlete_id=athlete.id, metric_id=metric.id, raw_value=12.0, derivation_method="post_station_split_penalty_v1",
        assessment_type="race_result", past_hyrox_result_id=result.id,
        recorded_at=datetime(2026, 9, 1), evidence_class="coach_derived",
    ))
    db_session.commit()


# ============================================================
# CapabilityScoreAssessment composite-FK cross-athlete/cross-metric rejection
# ============================================================

def test_score_assessment_cross_athlete_is_rejected(db_session):
    athlete1 = _athlete(db_session, "int-e1@example.com")
    athlete2 = _athlete(db_session, "int-e2@example.com")
    metric = _metric(db_session)

    score = _score(db_session, athlete1, metric)
    other_assessment = _assessment(db_session, athlete2, metric)

    db_session.add(CapabilityScoreAssessment(
        score_id=score.id, assessment_id=other_assessment.id, athlete_id=athlete1.id, metric_id=metric.id,
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_score_assessment_cross_metric_is_rejected(db_session):
    athlete = _athlete(db_session, "int-f1@example.com")
    metric1 = _metric(db_session, metric_id="threshold_pace_riegel_sec_per_km", capability_id="threshold_race_pace")
    metric2 = _metric(db_session, metric_id="wall_ball_no_rep_count", capability_id="station_economy", station="wall_balls")

    score = _score(db_session, athlete, metric1)
    other_metric_assessment = _assessment(db_session, athlete, metric2)

    db_session.add(CapabilityScoreAssessment(
        score_id=score.id, assessment_id=other_metric_assessment.id, athlete_id=athlete.id, metric_id=metric1.id,
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_score_assessment_dangling_score_is_rejected(db_session):
    athlete = _athlete(db_session, "int-g1@example.com")
    metric = _metric(db_session)
    assessment = _assessment(db_session, athlete, metric)

    db_session.add(CapabilityScoreAssessment(
        score_id="nonexistent-score-id", assessment_id=assessment.id, athlete_id=athlete.id, metric_id=metric.id,
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_score_assessment_same_athlete_metric_is_accepted(db_session):
    athlete = _athlete(db_session, "int-h1@example.com")
    metric = _metric(db_session)
    score = _score(db_session, athlete, metric)
    assessment = _assessment(db_session, athlete, metric)

    db_session.add(CapabilityScoreAssessment(
        score_id=score.id, assessment_id=assessment.id, athlete_id=athlete.id, metric_id=metric.id,
    ))
    db_session.commit()


# ============================================================
# CapabilityGap composite-FK rejection (score athlete/metric match, band-policy metric match)
# ============================================================

def test_gap_cross_athlete_score_is_rejected(db_session):
    athlete1 = _athlete(db_session, "int-i1@example.com")
    athlete2 = _athlete(db_session, "int-i2@example.com")
    metric = _metric(db_session)
    other_score = _score(db_session, athlete2, metric)

    db_session.add(CapabilityGap(
        athlete_id=athlete1.id, metric_id=metric.id, classification="unclassified", confidence="none",
        based_on_score_id=other_score.id, band_policy_id=None, computed_at=datetime(2026, 9, 1),
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_gap_cross_metric_score_is_rejected(db_session):
    athlete = _athlete(db_session, "int-j1@example.com")
    metric1 = _metric(db_session, metric_id="threshold_pace_riegel_sec_per_km", capability_id="threshold_race_pace")
    metric2 = _metric(db_session, metric_id="dead_hang_time_sec", capability_id="grip_postural_endurance")
    other_metric_score = _score(db_session, athlete, metric2)

    db_session.add(CapabilityGap(
        athlete_id=athlete.id, metric_id=metric1.id, classification="unclassified", confidence="none",
        based_on_score_id=other_metric_score.id, band_policy_id=None, computed_at=datetime(2026, 9, 1),
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_gap_cross_metric_band_policy_is_rejected(db_session):
    athlete = _athlete(db_session, "int-k1@example.com")
    metric1 = _metric(db_session, metric_id="threshold_pace_riegel_sec_per_km", capability_id="threshold_race_pace")
    metric2 = _metric(db_session, metric_id="dead_hang_time_sec", capability_id="grip_postural_endurance")
    score = _score(db_session, athlete, metric1)

    other_metric_policy = CapabilityBandPolicy(
        metric_id=metric2.id, version=1, effective_from=date(2026, 9, 1), notes="", evidence_class="coach_derived",
    )
    db_session.add(other_metric_policy)
    db_session.commit()

    db_session.add(CapabilityGap(
        athlete_id=athlete.id, metric_id=metric1.id, classification="weak", confidence="low",
        based_on_score_id=score.id, band_policy_id=other_metric_policy.id, computed_at=datetime(2026, 9, 1),
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_gap_dangling_band_policy_is_rejected(db_session):
    athlete = _athlete(db_session, "int-l1@example.com")
    metric = _metric(db_session)
    score = _score(db_session, athlete, metric)

    db_session.add(CapabilityGap(
        athlete_id=athlete.id, metric_id=metric.id, classification="weak", confidence="low",
        based_on_score_id=score.id, band_policy_id="nonexistent-policy-id", computed_at=datetime(2026, 9, 1),
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ============================================================
# CapabilityAssessment: derivation_method CHECKs
# ============================================================

def test_self_report_with_derivation_method_is_rejected(db_session):
    athlete = _athlete(db_session, "int-m1@example.com")
    metric = _metric(db_session)
    db_session.add(CapabilityAssessment(
        athlete_id=athlete.id, metric_id=metric.id, raw_value=300.0, derivation_method="should_be_null",
        assessment_type="self_report", recorded_at=datetime(2026, 9, 1), evidence_class="coach_derived",
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_logged_session_derived_without_derivation_method_is_rejected(db_session):
    athlete = _athlete(db_session, "int-n1@example.com")
    metric = _metric(db_session)
    block = TrainingBlock(athlete_id=athlete.id, start_date=date(2026, 1, 1), length_weeks=2)
    db_session.add(block)
    db_session.commit()
    week = TrainingWeek(block_id=block.id, week_number=1, phase="base")
    db_session.add(week)
    db_session.commit()
    workout = Workout(week_id=week.id, day_of_week=0, workout_type="strength", title="Forge", prescription={})
    db_session.add(workout)
    db_session.commit()

    db_session.add(CapabilityAssessment(
        athlete_id=athlete.id, metric_id=metric.id, raw_value=300.0, derivation_method=None,
        assessment_type="logged_session_derived", workout_id=workout.id,
        recorded_at=datetime(2026, 9, 1), evidence_class="coach_derived",
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ============================================================
# CapabilityAssessment: source-consistency CHECK
# ============================================================

def test_benchmark_result_type_without_benchmark_result_id_is_rejected(db_session):
    athlete = _athlete(db_session, "int-o1@example.com")
    metric = _metric(db_session)
    db_session.add(CapabilityAssessment(
        athlete_id=athlete.id, metric_id=metric.id, raw_value=300.0,
        assessment_type="benchmark_result", benchmark_result_id=None,
        recorded_at=datetime(2026, 9, 1), evidence_class="coach_derived",
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_self_report_with_a_source_fk_set_is_rejected(db_session):
    athlete = _athlete(db_session, "int-p1@example.com")
    metric = _metric(db_session, metric_id="vo2max_wearable_ml_kg_min", capability_id="aerobic_capacity")
    reading = RecoveryReading(athlete_id=athlete.id, reading_date=date(2026, 9, 1), source="apple_health", vo2_max=50.0)
    db_session.add(reading)
    db_session.commit()

    db_session.add(CapabilityAssessment(
        athlete_id=athlete.id, metric_id=metric.id, raw_value=50.0,
        assessment_type="self_report", recovery_reading_id=reading.id,
        recorded_at=datetime(2026, 9, 1), evidence_class="coach_derived",
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_valid_self_report_assessment_is_accepted(db_session):
    athlete = _athlete(db_session, "int-q1@example.com")
    metric = _metric(db_session)
    db_session.add(CapabilityAssessment(
        athlete_id=athlete.id, metric_id=metric.id, raw_value=300.0,
        assessment_type="self_report",
        recorded_at=datetime(2026, 9, 1), evidence_class="coach_derived",
    ))
    db_session.commit()


# ============================================================
# CapabilityGap: classification/confidence/band_policy CHECK, both directions
# ============================================================

def test_gap_unclassified_with_nonnull_band_policy_is_rejected(db_session):
    athlete = _athlete(db_session, "int-r1@example.com")
    metric = _metric(db_session)
    score = _score(db_session, athlete, metric)
    policy = CapabilityBandPolicy(metric_id=metric.id, version=1, effective_from=date(2026, 9, 1), notes="", evidence_class="coach_derived")
    db_session.add(policy)
    db_session.commit()

    db_session.add(CapabilityGap(
        athlete_id=athlete.id, metric_id=metric.id, classification="unclassified", confidence="none",
        based_on_score_id=score.id, band_policy_id=policy.id, computed_at=datetime(2026, 9, 1),
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_gap_unclassified_with_nonnone_confidence_is_rejected(db_session):
    athlete = _athlete(db_session, "int-s1@example.com")
    metric = _metric(db_session)
    score = _score(db_session, athlete, metric)

    db_session.add(CapabilityGap(
        athlete_id=athlete.id, metric_id=metric.id, classification="unclassified", confidence="high",
        based_on_score_id=score.id, band_policy_id=None, computed_at=datetime(2026, 9, 1),
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_gap_classified_with_null_band_policy_is_rejected(db_session):
    athlete = _athlete(db_session, "int-t1@example.com")
    metric = _metric(db_session)
    score = _score(db_session, athlete, metric)

    db_session.add(CapabilityGap(
        athlete_id=athlete.id, metric_id=metric.id, classification="weak", confidence="low",
        based_on_score_id=score.id, band_policy_id=None, computed_at=datetime(2026, 9, 1),
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_gap_classified_with_confidence_none_is_rejected(db_session):
    athlete = _athlete(db_session, "int-u1@example.com")
    metric = _metric(db_session)
    score = _score(db_session, athlete, metric)
    policy = CapabilityBandPolicy(metric_id=metric.id, version=1, effective_from=date(2026, 9, 1), notes="", evidence_class="coach_derived")
    db_session.add(policy)
    db_session.commit()

    db_session.add(CapabilityGap(
        athlete_id=athlete.id, metric_id=metric.id, classification="weak", confidence="none",
        based_on_score_id=score.id, band_policy_id=policy.id, computed_at=datetime(2026, 9, 1),
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_gap_classified_with_valid_policy_and_confidence_is_accepted(db_session):
    athlete = _athlete(db_session, "int-v1@example.com")
    metric = _metric(db_session)
    score = _score(db_session, athlete, metric)
    policy = CapabilityBandPolicy(metric_id=metric.id, version=1, effective_from=date(2026, 9, 1), notes="", evidence_class="coach_derived")
    db_session.add(policy)
    db_session.commit()

    db_session.add(CapabilityGap(
        athlete_id=athlete.id, metric_id=metric.id, classification="weak", confidence="low",
        based_on_score_id=score.id, band_policy_id=policy.id, computed_at=datetime(2026, 9, 1),
    ))
    db_session.commit()


# --- flag-reason consistency CHECK ---

def test_gap_flagged_without_reason_is_rejected(db_session):
    athlete = _athlete(db_session, "int-w1@example.com")
    metric = _metric(db_session)
    score = _score(db_session, athlete, metric)

    db_session.add(CapabilityGap(
        athlete_id=athlete.id, metric_id=metric.id, classification="unclassified", confidence="none",
        based_on_score_id=score.id, band_policy_id=None, flagged_for_reassessment=True, flag_reason=None,
        computed_at=datetime(2026, 9, 1),
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_gap_reason_without_flag_is_rejected(db_session):
    athlete = _athlete(db_session, "int-x1@example.com")
    metric = _metric(db_session)
    score = _score(db_session, athlete, metric)

    db_session.add(CapabilityGap(
        athlete_id=athlete.id, metric_id=metric.id, classification="unclassified", confidence="none",
        based_on_score_id=score.id, band_policy_id=None, flagged_for_reassessment=False, flag_reason="conflicting data",
        computed_at=datetime(2026, 9, 1),
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_gap_flagged_with_reason_is_accepted(db_session):
    athlete = _athlete(db_session, "int-y1@example.com")
    metric = _metric(db_session)
    score = _score(db_session, athlete, metric)

    db_session.add(CapabilityGap(
        athlete_id=athlete.id, metric_id=metric.id, classification="unclassified", confidence="none",
        based_on_score_id=score.id, band_policy_id=None, flagged_for_reassessment=True, flag_reason="conflicting data",
        computed_at=datetime(2026, 9, 1),
    ))
    db_session.commit()


# ============================================================
# CapabilityBand: interval CHECKs + uniqueness
# ============================================================

def _band_policy(db_session, metric):
    policy = CapabilityBandPolicy(metric_id=metric.id, version=1, effective_from=date(2026, 9, 1), notes="", evidence_class="coach_derived")
    db_session.add(policy)
    db_session.commit()
    return policy


def test_band_with_both_bounds_null_is_rejected(db_session):
    metric = _metric(db_session)
    policy = _band_policy(db_session, metric)
    db_session.add(CapabilityBand(band_policy_id=policy.id, label="adequate", lower_bound=None, upper_bound=None, sort_order=1))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_band_with_lower_gte_upper_is_rejected(db_session):
    metric = _metric(db_session)
    policy = _band_policy(db_session, metric)
    db_session.add(CapabilityBand(band_policy_id=policy.id, label="adequate", lower_bound=300.0, upper_bound=280.0, sort_order=1))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_band_duplicate_label_in_same_policy_is_rejected(db_session):
    metric = _metric(db_session)
    policy = _band_policy(db_session, metric)
    db_session.add(CapabilityBand(band_policy_id=policy.id, label="weak", lower_bound=None, upper_bound=310.0, sort_order=0))
    db_session.commit()

    db_session.add(CapabilityBand(band_policy_id=policy.id, label="weak", lower_bound=280.0, upper_bound=310.0, sort_order=1))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_band_duplicate_sort_order_in_same_policy_is_rejected(db_session):
    metric = _metric(db_session)
    policy = _band_policy(db_session, metric)
    db_session.add(CapabilityBand(band_policy_id=policy.id, label="weak", lower_bound=None, upper_bound=310.0, sort_order=0))
    db_session.commit()

    db_session.add(CapabilityBand(band_policy_id=policy.id, label="adequate", lower_bound=280.0, upper_bound=310.0, sort_order=0))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_band_valid_open_ended_top_band_is_accepted(db_session):
    metric = _metric(db_session)
    policy = _band_policy(db_session, metric)
    db_session.add(CapabilityBand(band_policy_id=policy.id, label="strong", lower_bound=None, upper_bound=250.0, sort_order=2))
    db_session.commit()


# ============================================================
# CapabilityBandPolicy config-integrity CHECKs
# ============================================================

def test_band_policy_version_zero_is_rejected(db_session):
    metric = _metric(db_session)
    db_session.add(CapabilityBandPolicy(metric_id=metric.id, version=0, effective_from=date(2026, 9, 1), notes="", evidence_class="coach_derived"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_band_policy_negative_hysteresis_margin_is_rejected(db_session):
    metric = _metric(db_session)
    db_session.add(CapabilityBandPolicy(
        metric_id=metric.id, version=1, hysteresis_margin_pct=-1.0, effective_from=date(2026, 9, 1), notes="", evidence_class="coach_derived",
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_band_policy_zero_hysteresis_repeat_count_is_rejected(db_session):
    metric = _metric(db_session)
    db_session.add(CapabilityBandPolicy(
        metric_id=metric.id, version=1, hysteresis_repeat_count=0, effective_from=date(2026, 9, 1), notes="", evidence_class="coach_derived",
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ============================================================
# CapabilityConfidenceRule: multiplicity uniqueness + config-integrity CHECKs
# ============================================================

def _confidence_policy(db_session, metric):
    policy = CapabilityConfidencePolicy(metric_id=metric.id, version=1, effective_from=date(2026, 9, 1), notes="")
    db_session.add(policy)
    db_session.commit()
    return policy


def test_confidence_rule_duplicate_tier_and_outcome_is_rejected(db_session):
    metric = _metric(db_session)
    policy = _confidence_policy(db_session, metric)
    db_session.add(CapabilityConfidenceRule(
        confidence_policy_id=policy.id, source_quality_tier="training_log",
        recency_window_days=42, min_data_points=1, requires_corroboration=False,
        resulting_confidence_tier="low", evaluation_order=0,
    ))
    db_session.commit()

    db_session.add(CapabilityConfidenceRule(
        confidence_policy_id=policy.id, source_quality_tier="training_log",
        recency_window_days=42, min_data_points=1, requires_corroboration=False,
        resulting_confidence_tier="low", evaluation_order=1,
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_confidence_rule_duplicate_tier_and_evaluation_order_is_rejected(db_session):
    metric = _metric(db_session)
    policy = _confidence_policy(db_session, metric)
    db_session.add(CapabilityConfidenceRule(
        confidence_policy_id=policy.id, source_quality_tier="training_log",
        recency_window_days=42, min_data_points=1, requires_corroboration=False,
        resulting_confidence_tier="low", evaluation_order=0,
    ))
    db_session.commit()

    db_session.add(CapabilityConfidenceRule(
        confidence_policy_id=policy.id, source_quality_tier="training_log",
        recency_window_days=84, min_data_points=3, requires_corroboration=False,
        resulting_confidence_tier="moderate", evaluation_order=0,
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_confidence_rule_multiple_outcomes_same_tier_is_accepted(db_session):
    """The point-5 fix: one source tier can legitimately produce several outcomes at
    increasing evidence thresholds, as long as tier+outcome and tier+priority are each unique."""
    metric = _metric(db_session)
    policy = _confidence_policy(db_session, metric)
    db_session.add(CapabilityConfidenceRule(
        confidence_policy_id=policy.id, source_quality_tier="training_log",
        recency_window_days=42, min_data_points=1, requires_corroboration=False,
        resulting_confidence_tier="low", evaluation_order=0,
    ))
    db_session.add(CapabilityConfidenceRule(
        confidence_policy_id=policy.id, source_quality_tier="training_log",
        recency_window_days=84, min_data_points=3, requires_corroboration=False,
        resulting_confidence_tier="moderate", evaluation_order=1,
    ))
    db_session.add(CapabilityConfidenceRule(
        confidence_policy_id=policy.id, source_quality_tier="training_log",
        recency_window_days=84, min_data_points=5, requires_corroboration=True, min_corroborating_count=2,
        resulting_confidence_tier="high", evaluation_order=2,
    ))
    db_session.commit()

    rules = db_session.query(CapabilityConfidenceRule).filter_by(confidence_policy_id=policy.id).all()
    assert len(rules) == 3


def test_confidence_rule_negative_evaluation_order_is_rejected(db_session):
    metric = _metric(db_session)
    policy = _confidence_policy(db_session, metric)
    db_session.add(CapabilityConfidenceRule(
        confidence_policy_id=policy.id, source_quality_tier="self_report",
        recency_window_days=42, min_data_points=1, requires_corroboration=False,
        resulting_confidence_tier="low", evaluation_order=-1,
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_confidence_rule_zero_recency_window_is_rejected(db_session):
    metric = _metric(db_session)
    policy = _confidence_policy(db_session, metric)
    db_session.add(CapabilityConfidenceRule(
        confidence_policy_id=policy.id, source_quality_tier="self_report",
        recency_window_days=0, min_data_points=1, requires_corroboration=False,
        resulting_confidence_tier="low", evaluation_order=0,
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_confidence_rule_zero_min_data_points_is_rejected(db_session):
    metric = _metric(db_session)
    policy = _confidence_policy(db_session, metric)
    db_session.add(CapabilityConfidenceRule(
        confidence_policy_id=policy.id, source_quality_tier="self_report",
        recency_window_days=42, min_data_points=0, requires_corroboration=False,
        resulting_confidence_tier="low", evaluation_order=0,
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_confidence_rule_requires_corroboration_without_min_count_is_rejected(db_session):
    metric = _metric(db_session)
    policy = _confidence_policy(db_session, metric)
    db_session.add(CapabilityConfidenceRule(
        confidence_policy_id=policy.id, source_quality_tier="direct_benchmark",
        recency_window_days=42, min_data_points=1, requires_corroboration=True, min_corroborating_count=None,
        resulting_confidence_tier="high", evaluation_order=0,
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_confidence_rule_no_corroboration_with_min_count_set_is_rejected(db_session):
    metric = _metric(db_session)
    policy = _confidence_policy(db_session, metric)
    db_session.add(CapabilityConfidenceRule(
        confidence_policy_id=policy.id, source_quality_tier="direct_benchmark",
        recency_window_days=42, min_data_points=1, requires_corroboration=False, min_corroborating_count=2,
        resulting_confidence_tier="high", evaluation_order=0,
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_confidence_policy_version_zero_is_rejected(db_session):
    metric = _metric(db_session)
    db_session.add(CapabilityConfidencePolicy(metric_id=metric.id, version=0, effective_from=date(2026, 9, 1), notes=""))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ============================================================
# Immutability — all 10 capability tables
# ============================================================

IMMUTABLE_CAPABILITY_MODELS = [
    "CapabilityDefinition",
    "CapabilityMetric",
    "CapabilityAssessment",
    "CapabilityScore",
    "CapabilityScoreAssessment",
    "CapabilityBandPolicy",
    "CapabilityBand",
    "CapabilityGap",
    "CapabilityConfidencePolicy",
    "CapabilityConfidenceRule",
]


def test_capability_definition_is_immutable(db_session):
    definition = CapabilityDefinition(id="tissue_capacity", name="Tissue Capacity", description="", measurement_hint="")
    db_session.add(definition)
    db_session.commit()

    definition.name = "changed"
    with pytest.raises(ImmutableRecordError):
        db_session.commit()
    db_session.rollback()
    assert db_session.get(CapabilityDefinition, "tissue_capacity").name == "Tissue Capacity"

    db_session.delete(db_session.get(CapabilityDefinition, "tissue_capacity"))
    with pytest.raises(ImmutableRecordError):
        db_session.commit()
    db_session.rollback()
    assert db_session.get(CapabilityDefinition, "tissue_capacity") is not None


def test_capability_metric_is_immutable(db_session):
    metric = _metric(db_session)

    metric.unit = "changed"
    with pytest.raises(ImmutableRecordError):
        db_session.commit()
    db_session.rollback()
    assert db_session.get(CapabilityMetric, metric.id).unit == "sec_per_km"


def test_capability_assessment_is_immutable(db_session):
    athlete = _athlete(db_session, "int-z1@example.com")
    metric = _metric(db_session)
    assessment = _assessment(db_session, athlete, metric)

    assessment.raw_value = 999.0
    with pytest.raises(ImmutableRecordError):
        db_session.commit()
    db_session.rollback()
    assert db_session.get(CapabilityAssessment, assessment.id).raw_value == 300.0

    db_session.delete(db_session.get(CapabilityAssessment, assessment.id))
    with pytest.raises(ImmutableRecordError):
        db_session.commit()
    db_session.rollback()
    assert db_session.get(CapabilityAssessment, assessment.id) is not None


def test_capability_score_is_immutable(db_session):
    athlete = _athlete(db_session, "int-z2@example.com")
    metric = _metric(db_session)
    score = _score(db_session, athlete, metric)

    score.value = 999.0
    with pytest.raises(ImmutableRecordError):
        db_session.commit()
    db_session.rollback()
    assert db_session.get(CapabilityScore, score.id).value == 300.0


def test_capability_score_assessment_is_immutable(db_session):
    athlete = _athlete(db_session, "int-z3@example.com")
    metric = _metric(db_session)
    score = _score(db_session, athlete, metric)
    assessment = _assessment(db_session, athlete, metric)
    link = CapabilityScoreAssessment(score_id=score.id, assessment_id=assessment.id, athlete_id=athlete.id, metric_id=metric.id)
    db_session.add(link)
    db_session.commit()

    db_session.delete(db_session.get(CapabilityScoreAssessment, link.id))
    with pytest.raises(ImmutableRecordError):
        db_session.commit()
    db_session.rollback()
    assert db_session.get(CapabilityScoreAssessment, link.id) is not None


def test_capability_band_policy_is_immutable(db_session):
    metric = _metric(db_session)
    policy = _band_policy(db_session, metric)

    policy.notes = "changed"
    with pytest.raises(ImmutableRecordError):
        db_session.commit()
    db_session.rollback()
    assert db_session.get(CapabilityBandPolicy, policy.id).notes == ""


def test_capability_band_is_immutable(db_session):
    metric = _metric(db_session)
    policy = _band_policy(db_session, metric)
    band = CapabilityBand(band_policy_id=policy.id, label="strong", lower_bound=None, upper_bound=250.0, sort_order=0)
    db_session.add(band)
    db_session.commit()

    band.sort_order = 5
    with pytest.raises(ImmutableRecordError):
        db_session.commit()
    db_session.rollback()
    assert db_session.get(CapabilityBand, band.id).sort_order == 0


def test_capability_gap_is_immutable(db_session):
    athlete = _athlete(db_session, "int-z4@example.com")
    metric = _metric(db_session)
    score = _score(db_session, athlete, metric)
    gap = CapabilityGap(
        athlete_id=athlete.id, metric_id=metric.id, classification="unclassified", confidence="none",
        based_on_score_id=score.id, band_policy_id=None, computed_at=datetime(2026, 9, 1),
    )
    db_session.add(gap)
    db_session.commit()

    gap.reasoning = "changed"
    with pytest.raises(ImmutableRecordError):
        db_session.commit()
    db_session.rollback()
    assert db_session.get(CapabilityGap, gap.id).reasoning == ""


def test_capability_confidence_policy_is_immutable(db_session):
    metric = _metric(db_session)
    policy = _confidence_policy(db_session, metric)

    policy.notes = "changed"
    with pytest.raises(ImmutableRecordError):
        db_session.commit()
    db_session.rollback()
    assert db_session.get(CapabilityConfidencePolicy, policy.id).notes == ""


def test_capability_confidence_rule_is_immutable(db_session):
    metric = _metric(db_session)
    policy = _confidence_policy(db_session, metric)
    rule = CapabilityConfidenceRule(
        confidence_policy_id=policy.id, source_quality_tier="training_log",
        recency_window_days=42, min_data_points=1, requires_corroboration=False,
        resulting_confidence_tier="low", evaluation_order=0,
    )
    db_session.add(rule)
    db_session.commit()

    rule.evaluation_order = 9
    with pytest.raises(ImmutableRecordError):
        db_session.commit()
    db_session.rollback()
    assert db_session.get(CapabilityConfidenceRule, rule.id).evaluation_order == 0


def test_session_usable_after_rejected_capability_update(db_session):
    metric = _metric(db_session)
    metric.unit = "changed"
    try:
        db_session.commit()
    except ImmutableRecordError:
        db_session.rollback()

    other = Athlete(email="still-usable-capability@example.com")
    db_session.add(other)
    db_session.commit()
    assert db_session.get(Athlete, other.id) is not None


# ============================================================
# No production code reads the new capability/benchmark tables
# ============================================================

def test_no_production_code_reads_capability_tables_outside_their_own_modules():
    result = subprocess.run(
        ["grep", "-rl", "-e", "Capability", "-e", "BenchmarkDefinition", "-e", "BenchmarkResult", "app/services/", "app/api/"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    referencing_files = {line for line in result.stdout.splitlines() if line}
    assert referencing_files == set(), f"Unexpected capability-table reference(s) in services/routes: {referencing_files}"


def test_program_engine_and_movement_library_do_not_reference_capability_tables():
    for path in ("app/services/program_engine.py", "app/services/movement_library.py"):
        result = subprocess.run(["grep", "-c", "Capability", path], cwd=REPO_ROOT, capture_output=True, text=True)
        assert result.stdout.strip() in ("0", ""), f"{path} unexpectedly references Capability* ({result.stdout.strip()} matches)"
