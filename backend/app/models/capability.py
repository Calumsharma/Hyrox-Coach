"""Program Engine v5 Milestone 1B — capability measurement foundation.

Ten tables implementing the approved Milestone 1B plan (see happy-weaving-raven.md, §A-F):
CapabilityDefinition and CapabilityMetric are immutable seed definitions; CapabilityAssessment
is an immutable evidence point (direct or a deterministic feature extracted from an existing
source — never invented); CapabilityScore/CapabilityScoreAssessment/CapabilityGap are the
append-only measurement -> lineage -> interpretation chain, linked by composite foreign keys
so a score or gap can never cite another athlete's or another metric's evidence; and
CapabilityBandPolicy/CapabilityBand/CapabilityConfidencePolicy/CapabilityConfidenceRule are
versioned, coach-authored config that starts empty — no numeric thresholds are seeded here.

This module contains ONLY schema. No scoring, confidence, or classification logic exists here
or anywhere else in the codebase yet — see the plan's §F for what's deliberately deferred.
"""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import (
    AssessmentType,
    BandLabel,
    CapabilityClassification,
    CapabilityConfidence,
    ConfidenceTier,
    Division,
    EvidenceClass,
    SourceQualityTier,
)
from app.models.immutability import enforce_immutable


def _uuid() -> str:
    return str(uuid.uuid4())


class CapabilityDefinition(Base):
    """Immutable seed definition. The 10 abstract capability domains — see spec §4.1. A
    material change to what a capability means creates a new id, never an edit."""

    __tablename__ = "capability_definitions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text, default="")
    measurement_hint: Mapped[str] = mapped_column(Text, default="")


class CapabilityMetric(Base):
    """Immutable seed definition. Resolves "station economy has no one unit" — every
    measurable thing is its own metric row, in its own unit. A materially different protocol
    or unit is a new metric id, never an edit to an existing row."""

    __tablename__ = "capability_metrics"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    capability_id: Mapped[str] = mapped_column(
        String, ForeignKey("capability_definitions.id", ondelete="RESTRICT"), nullable=False
    )
    station: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    unit: Mapped[str] = mapped_column(String, nullable=False)
    higher_is_better: Mapped[bool] = mapped_column(Boolean, nullable=False)
    evidence_class: Mapped[EvidenceClass] = mapped_column(String, default=EvidenceClass.COACH_DERIVED)
    description: Mapped[str] = mapped_column(Text, default="")


class CapabilityAssessment(Base):
    """Immutable. "An immutable, source-linked evidence point expressed in one CapabilityMetric's
    unit. It may be a direct measurement or a deterministic feature extracted from an existing
    source." `derivation_method` is NULL for a direct measurement, set to a versioned slug for
    a computed feature. Source ownership is enforced by composite FK, for every source table
    that carries athlete_id directly (BenchmarkResult/RecoveryReading/PastHyroxResult) — a
    cited source row must belong to the same athlete. `workout_id` is a simple FK only:
    Workout reaches its athlete indirectly (Workout -> TrainingWeek -> TrainingBlock -> Athlete),
    so athlete ownership for workout-derived assessments is a Milestone 2 service-layer
    invariant, not a database guarantee here — no logged_session_derived assessment is created
    anywhere in this milestone, so the gap has zero live exposure yet.
    """

    __tablename__ = "capability_assessments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["benchmark_result_id", "athlete_id"],
            ["benchmark_results.id", "benchmark_results.athlete_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["recovery_reading_id", "athlete_id"],
            ["recovery_readings.id", "recovery_readings.athlete_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["past_hyrox_result_id", "athlete_id"],
            ["past_hyrox_results.id", "past_hyrox_results.athlete_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("id", "athlete_id", "metric_id"),
        CheckConstraint("assessment_type != 'self_report' OR derivation_method IS NULL"),
        CheckConstraint("assessment_type != 'logged_session_derived' OR derivation_method IS NOT NULL"),
        CheckConstraint(
            "(assessment_type = 'benchmark_result' AND benchmark_result_id IS NOT NULL "
            "AND workout_id IS NULL AND recovery_reading_id IS NULL AND past_hyrox_result_id IS NULL) "
            "OR (assessment_type = 'logged_session_derived' AND workout_id IS NOT NULL "
            "AND benchmark_result_id IS NULL AND recovery_reading_id IS NULL AND past_hyrox_result_id IS NULL) "
            "OR (assessment_type = 'wearable_derived' AND recovery_reading_id IS NOT NULL "
            "AND benchmark_result_id IS NULL AND workout_id IS NULL AND past_hyrox_result_id IS NULL) "
            "OR (assessment_type = 'race_result' AND past_hyrox_result_id IS NOT NULL "
            "AND benchmark_result_id IS NULL AND workout_id IS NULL AND recovery_reading_id IS NULL) "
            "OR (assessment_type = 'self_report' AND benchmark_result_id IS NULL "
            "AND workout_id IS NULL AND recovery_reading_id IS NULL AND past_hyrox_result_id IS NULL)",
            name="ck_capability_assessment_source_consistency",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id", ondelete="RESTRICT"), nullable=False)
    metric_id: Mapped[str] = mapped_column(
        String, ForeignKey("capability_metrics.id", ondelete="RESTRICT"), nullable=False
    )
    raw_value: Mapped[float] = mapped_column(Float, nullable=False)
    derivation_method: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    assessment_type: Mapped[AssessmentType] = mapped_column(String, nullable=False)

    benchmark_result_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    workout_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("workouts.id", ondelete="RESTRICT"), nullable=True
    )
    recovery_reading_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    past_hyrox_result_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    division: Mapped[Optional[Division]] = mapped_column(String, nullable=True)
    rule_set_version_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("race_rule_sets.id", ondelete="RESTRICT"), nullable=True
    )
    context_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    evidence_class: Mapped[EvidenceClass] = mapped_column(String, default=EvidenceClass.COACH_DERIVED)


class CapabilityScore(Base):
    """Append-only. The current synthesized/aggregated state calculated from one or more
    CapabilityAssessment evidence points for the same metric — see CapabilityScoreAssessment
    for the lineage join. Recomputation appends a new row; never updated in place."""

    __tablename__ = "capability_scores"
    __table_args__ = (UniqueConstraint("id", "athlete_id", "metric_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id", ondelete="RESTRICT"), nullable=False)
    metric_id: Mapped[str] = mapped_column(
        String, ForeignKey("capability_metrics.id", ondelete="RESTRICT"), nullable=False
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    computation_method: Mapped[str] = mapped_column(String, nullable=False)
    evidence_class: Mapped[EvidenceClass] = mapped_column(String, default=EvidenceClass.COACH_DERIVED)
    computed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CapabilityScoreAssessment(Base):
    """Append-only. Normalized lineage join, replacing a JSON list of ids — both composite
    foreign keys below pin the SAME locally-stored (athlete_id, metric_id) pair, so the
    database transitively guarantees the cited score and assessment share both. A cross-
    athlete or cross-metric citation cannot be inserted."""

    __tablename__ = "capability_score_assessments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["score_id", "athlete_id", "metric_id"],
            ["capability_scores.id", "capability_scores.athlete_id", "capability_scores.metric_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["assessment_id", "athlete_id", "metric_id"],
            ["capability_assessments.id", "capability_assessments.athlete_id", "capability_assessments.metric_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("score_id", "assessment_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    score_id: Mapped[str] = mapped_column(String, nullable=False)
    assessment_id: Mapped[str] = mapped_column(String, nullable=False)
    # Denormalized, not independently settable in practice — only ever written by the code
    # that creates the score, required so both composite FKs above can anchor to one pair.
    athlete_id: Mapped[str] = mapped_column(String, nullable=False)
    metric_id: Mapped[str] = mapped_column(String, nullable=False)


class CapabilityBandPolicy(Base):
    """Append-only by version — a policy change is a new (metric_id, version) row, never an
    edit. Scoped by metric_id alone (which already encodes capability + station); no sex/
    division/experience columns, since experience should influence prescription conservatism,
    not redefine physiological capability, and any real context-specific banding is expressed
    via additional CapabilityMetric rows where the distinction is real, not speculative
    columns here. Starts empty — no band values are seeded in Milestone 1B."""

    __tablename__ = "capability_band_policies"
    __table_args__ = (
        UniqueConstraint("metric_id", "version"),
        UniqueConstraint("id", "metric_id"),
        CheckConstraint("version > 0"),
        CheckConstraint("hysteresis_margin_pct IS NULL OR hysteresis_margin_pct >= 0"),
        CheckConstraint("hysteresis_repeat_count IS NULL OR hysteresis_repeat_count > 0"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    metric_id: Mapped[str] = mapped_column(
        String, ForeignKey("capability_metrics.id", ondelete="RESTRICT"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    hysteresis_margin_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hysteresis_repeat_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    evidence_class: Mapped[EvidenceClass] = mapped_column(String, default=EvidenceClass.COACH_DERIVED)


class CapabilityBand(Base):
    """Immutable — a child of an append-only-by-version policy, so it never changes once its
    parent version exists. lower_bound/upper_bound with explicit inclusivity flags replace a
    single ambiguous boundary value; the two CHECK constraints below reject a fully-unbounded
    band and a non-positive interval. Overlap/full-coverage validation across a policy's
    sibling bands is Milestone 2 service logic — CHECK constraints can't reason across rows."""

    __tablename__ = "capability_bands"
    __table_args__ = (
        UniqueConstraint("band_policy_id", "label"),
        UniqueConstraint("band_policy_id", "sort_order"),
        CheckConstraint("lower_bound IS NOT NULL OR upper_bound IS NOT NULL"),
        CheckConstraint("lower_bound IS NULL OR upper_bound IS NULL OR lower_bound < upper_bound"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    band_policy_id: Mapped[str] = mapped_column(
        String, ForeignKey("capability_band_policies.id", ondelete="RESTRICT"), nullable=False
    )
    label: Mapped[BandLabel] = mapped_column(String, nullable=False)
    lower_bound: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lower_inclusive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    upper_bound: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    upper_inclusive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)


class CapabilityGap(Base):
    """Append-only. The interpretation layer — the only thing a future generator reads
    directly, so athlete_id/metric_id are kept as real, queryable columns rather than derived
    purely through the cited score. Consistency is not left to application code: the two
    composite FKs below force the cited score and band policy to belong to THIS gap's own
    athlete/metric. A row only exists once a score exists (based_on_score_id is NOT NULL) —
    "no data at all" is no row, never a null-score row. The CHECK constraint ties
    classification, band_policy_id and confidence together in both directions: unclassified
    means no policy and no confidence; classified means both are present."""

    __tablename__ = "capability_gaps"
    __table_args__ = (
        ForeignKeyConstraint(
            ["based_on_score_id", "athlete_id", "metric_id"],
            ["capability_scores.id", "capability_scores.athlete_id", "capability_scores.metric_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["band_policy_id", "metric_id"],
            ["capability_band_policies.id", "capability_band_policies.metric_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "(classification = 'unclassified' AND band_policy_id IS NULL AND confidence = 'none') "
            "OR (classification != 'unclassified' AND band_policy_id IS NOT NULL AND confidence != 'none')",
            name="ck_capability_gap_classification_consistency",
        ),
        CheckConstraint(
            "(flagged_for_reassessment = FALSE AND flag_reason IS NULL) "
            "OR (flagged_for_reassessment = TRUE AND flag_reason IS NOT NULL)",
            name="ck_capability_gap_flag_reason_consistency",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    athlete_id: Mapped[str] = mapped_column(String, nullable=False)
    metric_id: Mapped[str] = mapped_column(String, nullable=False)
    classification: Mapped[CapabilityClassification] = mapped_column(String, nullable=False)
    confidence: Mapped[CapabilityConfidence] = mapped_column(String, nullable=False)
    based_on_score_id: Mapped[str] = mapped_column(String, nullable=False)
    band_policy_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    reasoning: Mapped[str] = mapped_column(Text, default="")
    flagged_for_reassessment: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    flag_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CapabilityConfidencePolicy(Base):
    """Append-only by version, scoped by metric_id. No numeric values live on this row — they
    live on CapabilityConfidenceRule, so each source-quality tier's rule is its own queryable
    row rather than a blob. Starts empty — no rows seeded in Milestone 1B."""

    __tablename__ = "capability_confidence_policies"
    __table_args__ = (
        UniqueConstraint("metric_id", "version"),
        CheckConstraint("version > 0"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    metric_id: Mapped[str] = mapped_column(
        String, ForeignKey("capability_metrics.id", ondelete="RESTRICT"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="")


class CapabilityConfidenceRule(Base):
    """Immutable — a child of an append-only-by-version policy. One source-quality tier can
    legitimately produce several outcomes at increasing evidence thresholds (e.g. one training
    observation -> low, three consistent -> moderate, repeated plus corroboration -> high) —
    the two UNIQUE constraints below prevent duplicate tier-to-outcome pairs and priority ties,
    so future evaluation ("the highest-evaluation_order rule whose conditions are satisfied")
    is deterministic by construction. No rows are seeded in Milestone 1B, and no partially
    configured row can ever be created: recency_window_days/min_data_points are required
    (not nullable) and must be positive, and min_corroborating_count is required and positive
    exactly when requires_corroboration is true."""

    __tablename__ = "capability_confidence_rules"
    __table_args__ = (
        UniqueConstraint("confidence_policy_id", "source_quality_tier", "resulting_confidence_tier"),
        UniqueConstraint("confidence_policy_id", "source_quality_tier", "evaluation_order"),
        CheckConstraint("recency_window_days > 0"),
        CheckConstraint("min_data_points > 0"),
        CheckConstraint("evaluation_order >= 0"),
        CheckConstraint(
            "(requires_corroboration = FALSE AND min_corroborating_count IS NULL) "
            "OR (requires_corroboration = TRUE AND min_corroborating_count IS NOT NULL AND min_corroborating_count > 0)",
            name="ck_capability_confidence_rule_corroboration_consistency",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    confidence_policy_id: Mapped[str] = mapped_column(
        String, ForeignKey("capability_confidence_policies.id", ondelete="RESTRICT"), nullable=False
    )
    source_quality_tier: Mapped[SourceQualityTier] = mapped_column(String, nullable=False)
    # No CapabilityConfidenceRule row is seeded in Milestone 1B (per the plan and this
    # milestone's own instructions) — but any row that IS ever created must be fully
    # configured, never partial: both fields are required, not "nullable, unset for now".
    recency_window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    min_data_points: Mapped[int] = mapped_column(Integer, nullable=False)
    requires_corroboration: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    min_corroborating_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    resulting_confidence_tier: Mapped[ConfidenceTier] = mapped_column(String, nullable=False)
    evaluation_order: Mapped[int] = mapped_column(Integer, nullable=False)


for _model in (
    CapabilityDefinition,
    CapabilityMetric,
    CapabilityAssessment,
    CapabilityScore,
    CapabilityScoreAssessment,
    CapabilityBandPolicy,
    CapabilityBand,
    CapabilityGap,
    CapabilityConfidencePolicy,
    CapabilityConfidenceRule,
):
    enforce_immutable(_model)
