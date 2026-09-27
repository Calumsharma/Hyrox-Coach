"""Deterministic, provisional latest-assessment selection — Program Engine v5 Milestone 2, plan
§D4. A UUID must never decide which physiological evidence is current — only used, elsewhere, to
stabilize presentation ordering. Inactive source evidence is excluded before selection is even
attempted (step 0)."""

import uuid
from datetime import datetime

import pytest

from app.models import Athlete, CapabilityAssessment, CapabilityDefinition, CapabilityMetric, RecoveryReading
from app.models.enums import WearableProvider
from app.services.capability_scoring import (
    compute_score_from_current_assessment,
    is_source_evidence_active,
    select_current_assessment,
)


def _athlete(db_session, email="scoring@example.com"):
    a = Athlete(email=email)
    db_session.add(a)
    db_session.commit()
    return a


def _metric(db_session, metric_id="threshold_pace_riegel_sec_per_km", capability_id="threshold_race_pace"):
    if db_session.get(CapabilityDefinition, capability_id) is None:
        db_session.add(CapabilityDefinition(id=capability_id, name=capability_id, description="", measurement_hint=""))
        db_session.commit()
    m = CapabilityMetric(
        id=metric_id, capability_id=capability_id, station=None, unit="sec_per_km",
        higher_is_better=False, evidence_class="coach_derived", description="",
    )
    db_session.add(m)
    db_session.commit()
    return m


def _assessment(db_session, athlete, metric, **overrides):
    # Defaults to self_report — the one assessment_type whose source-consistency CHECK requires
    # every optional source id to be NULL, so a bare assessment needs no BenchmarkResult/
    # RecoveryReading/etc. row unless a test explicitly overrides assessment_type/derivation_method.
    defaults = dict(
        id=str(uuid.uuid4()), athlete_id=athlete.id, metric_id=metric.id, raw_value=300.0,
        derivation_method=None, assessment_type="self_report",
        recorded_at=datetime(2026, 9, 1), ingested_at=datetime(2026, 9, 1),
        source_revision=None, evidence_class="coach_derived",
    )
    defaults.update(overrides)
    a = CapabilityAssessment(**defaults)
    db_session.add(a)
    db_session.commit()
    return a


def test_no_assessments_is_no_current_evidence(db_session):
    athlete = _athlete(db_session)
    metric = _metric(db_session)
    result = select_current_assessment(db_session, athlete.id, metric.id)
    assert result.status == "no_current_evidence"


def test_single_latest_wins_outright(db_session):
    athlete = _athlete(db_session)
    metric = _metric(db_session)
    _assessment(db_session, athlete, metric, recorded_at=datetime(2026, 8, 1))
    latest = _assessment(db_session, athlete, metric, recorded_at=datetime(2026, 9, 1))

    result = select_current_assessment(db_session, athlete.id, metric.id)
    assert result.status == "resolved"
    assert result.assessment.id == latest.id


def test_same_lineage_tie_broken_by_ingested_at(db_session):
    athlete = _athlete(db_session)
    metric = _metric(db_session, metric_id="vo2max_wearable_ml_kg_min", capability_id="aerobic_capacity")
    tied_time = datetime(2026, 9, 1)
    reading = RecoveryReading(athlete_id=athlete.id, reading_date=tied_time.date(), source=WearableProvider.APPLE_HEALTH, vo2_max=50.0)
    db_session.add(reading)
    db_session.commit()

    earlier = _assessment(
        db_session, athlete, metric, assessment_type="wearable_derived", recovery_reading_id=reading.id,
        recorded_at=tied_time, ingested_at=datetime(2026, 9, 1, 8, 0), source_revision="rev-1",
    )
    later = _assessment(
        db_session, athlete, metric, assessment_type="wearable_derived", recovery_reading_id=reading.id,
        recorded_at=tied_time, ingested_at=datetime(2026, 9, 1, 12, 0), source_revision="rev-2",
    )

    result = select_current_assessment(db_session, athlete.id, metric.id)
    assert result.status == "resolved"
    assert result.assessment.id == later.id
    assert result.assessment.id != earlier.id


def test_10k_beats_5k_on_tied_recorded_at(db_session):
    from app.models import BenchmarkDefinition, BenchmarkResult

    athlete = _athlete(db_session)
    metric = _metric(db_session)
    tied_time = datetime(2026, 9, 1)
    db_session.add(BenchmarkDefinition(id="benchmark_5k_time_trial", name="5K Time Trial", protocol_description="", unit="sec", evidence_class="coach_derived"))
    db_session.add(BenchmarkDefinition(id="benchmark_10k_time_trial", name="10K Time Trial", protocol_description="", unit="sec", evidence_class="coach_derived"))
    db_session.commit()
    five_k_result = BenchmarkResult(athlete_id=athlete.id, benchmark_id="benchmark_5k_time_trial", completed_at=tied_time, raw_value=1200.0, context={}, notes="")
    ten_k_result = BenchmarkResult(athlete_id=athlete.id, benchmark_id="benchmark_10k_time_trial", completed_at=tied_time, raw_value=2400.0, context={}, notes="")
    db_session.add_all([five_k_result, ten_k_result])
    db_session.commit()

    five_k = _assessment(
        db_session, athlete, metric, assessment_type="benchmark_result", benchmark_result_id=five_k_result.id,
        derivation_method="riegel_threshold_pace_from_5k_v1",
        recorded_at=tied_time, ingested_at=datetime(2026, 9, 1, 8, 0),
    )
    ten_k = _assessment(
        db_session, athlete, metric, assessment_type="benchmark_result", benchmark_result_id=ten_k_result.id,
        derivation_method="pace_from_10k_time_trial_v1",
        recorded_at=tied_time, ingested_at=datetime(2026, 9, 1, 7, 0),  # earlier ingestion, still wins
    )

    result = select_current_assessment(db_session, athlete.id, metric.id)
    assert result.status == "resolved"
    assert result.assessment.id == ten_k.id
    assert result.assessment.id != five_k.id


def test_unresolvable_tie_is_ambiguous_evidence(db_session):
    """A self-report and a (synthetic, distinctly-named) wearable-derived assessment, tied on
    recorded_at, with no stated precedence rule between them — the one real precedence rule this
    milestone defines is specifically 10K-vs-5K, so a genuinely different pair of lineages must
    resolve as ambiguous, never silently picked."""
    athlete = _athlete(db_session)
    metric = _metric(db_session)
    tied_time = datetime(2026, 9, 1)

    reading = RecoveryReading(
        athlete_id=athlete.id, reading_date=tied_time.date(), source=WearableProvider.APPLE_HEALTH, vo2_max=99.0
    )
    db_session.add(reading)
    db_session.commit()

    a1 = _assessment(
        db_session, athlete, metric, assessment_type="self_report", derivation_method=None,
        recorded_at=tied_time, ingested_at=tied_time,
    )
    a2 = _assessment(
        db_session, athlete, metric, assessment_type="wearable_derived", derivation_method="synthetic_alt_method_v1",
        recovery_reading_id=reading.id, recorded_at=tied_time, ingested_at=tied_time, source_revision="rev-x",
    )

    result = select_current_assessment(db_session, athlete.id, metric.id)
    assert result.status == "ambiguous_evidence"
    assert set(result.competing_assessment_ids) == {a1.id, a2.id}


def test_inactive_wearable_evidence_excluded_before_selection(db_session):
    athlete = _athlete(db_session)
    metric = _metric(db_session, metric_id="vo2max_wearable_ml_kg_min", capability_id="aerobic_capacity")
    reading = RecoveryReading(athlete_id=athlete.id, reading_date=datetime(2026, 8, 1).date(), source=WearableProvider.APPLE_HEALTH, vo2_max=None)
    db_session.add(reading)
    db_session.commit()

    stale = _assessment(
        db_session, athlete, metric, assessment_type="wearable_derived",
        recovery_reading_id=reading.id, recorded_at=datetime(2026, 8, 1), source_revision="rev-1",
    )

    assert is_source_evidence_active(db_session, stale) is False
    result = select_current_assessment(db_session, athlete.id, metric.id)
    assert result.status == "no_current_evidence"


def test_benchmark_derived_evidence_always_active(db_session):
    athlete = _athlete(db_session)
    metric = _metric(db_session)
    a = _assessment(db_session, athlete, metric)
    assert is_source_evidence_active(db_session, a) is True


def test_compute_score_returns_none_when_ambiguous(db_session):
    athlete = _athlete(db_session)
    metric = _metric(db_session)
    tied_time = datetime(2026, 9, 1)
    reading = RecoveryReading(athlete_id=athlete.id, reading_date=tied_time.date(), source=WearableProvider.APPLE_HEALTH, vo2_max=99.0)
    db_session.add(reading)
    db_session.commit()

    _assessment(db_session, athlete, metric, assessment_type="self_report", recorded_at=tied_time, ingested_at=tied_time)
    _assessment(
        db_session, athlete, metric, assessment_type="wearable_derived", derivation_method="synthetic_alt_method_v1",
        recovery_reading_id=reading.id, recorded_at=tied_time, ingested_at=tied_time, source_revision="rev-y",
    )

    score = compute_score_from_current_assessment(db_session, athlete.id, metric.id)
    assert score is None


def test_compute_score_links_lineage_to_winning_assessment(db_session):
    from app.models import CapabilityScoreAssessment

    athlete = _athlete(db_session)
    metric = _metric(db_session)
    winner = _assessment(db_session, athlete, metric, raw_value=250.0, recorded_at=datetime(2026, 9, 1))

    score = compute_score_from_current_assessment(db_session, athlete.id, metric.id)
    assert score is not None
    assert score.value == 250.0

    link = (
        db_session.query(CapabilityScoreAssessment)
        .filter(CapabilityScoreAssessment.score_id == score.id)
        .first()
    )
    assert link is not None
    assert link.assessment_id == winner.id
