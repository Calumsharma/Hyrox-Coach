"""CRUD/relationship round-trip for the 10 capability tables — Program Engine v5 Milestone 1B.
Referential-integrity (composite FK / CHECK constraint) behavior lives in
test_capability_integrity.py; this file only proves each table creates and reads back correctly.
"""

from datetime import date, datetime

from app.models import (
    Athlete,
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
)


def _athlete(db_session, email="capability@example.com"):
    athlete = Athlete(email=email)
    db_session.add(athlete)
    db_session.commit()
    return athlete


def _definition_and_metric(db_session, capability_id="threshold_race_pace", metric_id="threshold_pace_riegel_sec_per_km"):
    definition = CapabilityDefinition(id=capability_id, name="Threshold & Race Pace", description="", measurement_hint="")
    metric = CapabilityMetric(
        id=metric_id,
        capability_id=capability_id,
        station=None,
        unit="sec_per_km",
        higher_is_better=False,
        evidence_class="coach_derived",
        description="",
    )
    db_session.add_all([definition, metric])
    db_session.commit()
    return definition, metric


def test_capability_definition_create_and_read(db_session):
    definition, _ = _definition_and_metric(db_session)
    fetched = db_session.get(CapabilityDefinition, definition.id)
    assert fetched.name == "Threshold & Race Pace"


def test_capability_metric_create_and_read(db_session):
    _, metric = _definition_and_metric(db_session)
    fetched = db_session.get(CapabilityMetric, metric.id)
    assert fetched.capability_id == "threshold_race_pace"
    assert fetched.unit == "sec_per_km"
    assert fetched.higher_is_better is False


def test_capability_assessment_create_and_read(db_session):
    athlete = _athlete(db_session)
    _, metric = _definition_and_metric(db_session)

    assessment = CapabilityAssessment(
        athlete_id=athlete.id,
        metric_id=metric.id,
        raw_value=310.5,
        derivation_method=None,
        assessment_type="self_report",
        recorded_at=datetime(2026, 9, 1),
        evidence_class="coach_derived",
        ingested_at=datetime(2026, 9, 1),  # Program Engine v5 Milestone 2 (migration 0005): NOT NULL
    )
    db_session.add(assessment)
    db_session.commit()

    fetched = db_session.get(CapabilityAssessment, assessment.id)
    assert fetched.raw_value == 310.5
    assert fetched.derivation_method is None
    assert fetched.assessment_type == "self_report"


def test_capability_score_create_and_read(db_session):
    athlete = _athlete(db_session)
    _, metric = _definition_and_metric(db_session)

    score = CapabilityScore(
        athlete_id=athlete.id,
        metric_id=metric.id,
        value=305.0,
        computation_method="riegel_threshold_pace_v1",
        evidence_class="coach_derived",
        computed_at=datetime(2026, 9, 1),
    )
    db_session.add(score)
    db_session.commit()

    fetched = db_session.get(CapabilityScore, score.id)
    assert fetched.value == 305.0
    assert fetched.computation_method == "riegel_threshold_pace_v1"


def test_capability_score_assessment_lineage_create_and_read(db_session):
    athlete = _athlete(db_session)
    _, metric = _definition_and_metric(db_session)

    assessment = CapabilityAssessment(
        athlete_id=athlete.id, metric_id=metric.id, raw_value=310.5,
        assessment_type="self_report", recorded_at=datetime(2026, 9, 1), evidence_class="coach_derived",
        ingested_at=datetime(2026, 9, 1),  # Program Engine v5 Milestone 2 (migration 0005): NOT NULL
    )
    score = CapabilityScore(
        athlete_id=athlete.id, metric_id=metric.id, value=310.5,
        computation_method="riegel_threshold_pace_v1", evidence_class="coach_derived", computed_at=datetime(2026, 9, 1),
    )
    db_session.add_all([assessment, score])
    db_session.commit()

    link = CapabilityScoreAssessment(
        score_id=score.id, assessment_id=assessment.id, athlete_id=athlete.id, metric_id=metric.id,
    )
    db_session.add(link)
    db_session.commit()

    fetched = db_session.get(CapabilityScoreAssessment, link.id)
    assert fetched.score_id == score.id
    assert fetched.assessment_id == assessment.id


def test_capability_band_policy_and_band_create_and_read(db_session):
    _, metric = _definition_and_metric(db_session)

    policy = CapabilityBandPolicy(
        metric_id=metric.id, version=1, effective_from=date(2026, 9, 1), notes="", evidence_class="coach_derived",
    )
    db_session.add(policy)
    db_session.commit()

    weak = CapabilityBand(band_policy_id=policy.id, label="weak", lower_bound=None, upper_bound=310.0, sort_order=0)
    adequate = CapabilityBand(band_policy_id=policy.id, label="adequate", lower_bound=280.0, upper_bound=310.0, sort_order=1)
    strong = CapabilityBand(band_policy_id=policy.id, label="strong", lower_bound=None, upper_bound=280.0, sort_order=2)
    db_session.add_all([weak, adequate, strong])
    db_session.commit()

    fetched_policy = db_session.get(CapabilityBandPolicy, policy.id)
    assert fetched_policy.version == 1
    assert fetched_policy.hysteresis_margin_pct is None

    bands = db_session.query(CapabilityBand).filter_by(band_policy_id=policy.id).order_by(CapabilityBand.sort_order).all()
    assert [b.label for b in bands] == ["weak", "adequate", "strong"]


def test_capability_gap_create_and_read(db_session):
    athlete = _athlete(db_session)
    _, metric = _definition_and_metric(db_session)

    score = CapabilityScore(
        athlete_id=athlete.id, metric_id=metric.id, value=305.0,
        computation_method="riegel_threshold_pace_v1", evidence_class="coach_derived", computed_at=datetime(2026, 9, 1),
    )
    db_session.add(score)
    db_session.commit()

    gap = CapabilityGap(
        athlete_id=athlete.id,
        metric_id=metric.id,
        classification="unclassified",
        confidence="none",
        based_on_score_id=score.id,
        band_policy_id=None,
        reasoning="No CapabilityBandPolicy exists yet for this metric.",
        computed_at=datetime(2026, 9, 1),
    )
    db_session.add(gap)
    db_session.commit()

    fetched = db_session.get(CapabilityGap, gap.id)
    assert fetched.classification == "unclassified"
    assert fetched.confidence == "none"
    assert fetched.band_policy_id is None
    assert fetched.flagged_for_reassessment is False
    assert fetched.flag_reason is None


def test_capability_confidence_policy_and_rule_create_and_read(db_session):
    _, metric = _definition_and_metric(db_session)

    policy = CapabilityConfidencePolicy(metric_id=metric.id, version=1, effective_from=date(2026, 9, 1), notes="")
    db_session.add(policy)
    db_session.commit()

    rule = CapabilityConfidenceRule(
        confidence_policy_id=policy.id,
        source_quality_tier="training_log",
        recency_window_days=42,
        min_data_points=3,
        requires_corroboration=True,
        min_corroborating_count=2,
        resulting_confidence_tier="moderate",
        evaluation_order=1,
    )
    db_session.add(rule)
    db_session.commit()

    fetched_policy = db_session.get(CapabilityConfidencePolicy, policy.id)
    assert fetched_policy.version == 1

    fetched_rule = db_session.get(CapabilityConfidenceRule, rule.id)
    assert fetched_rule.source_quality_tier == "training_log"
    assert fetched_rule.resulting_confidence_tier == "moderate"
    assert fetched_rule.evaluation_order == 1
