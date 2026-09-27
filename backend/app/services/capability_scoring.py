"""Deterministic, provisional latest-assessment selection and scoring — Program Engine v5
Milestone 2, plan §D4/§D5.

`select_current_assessment` never uses a UUID to decide which physiological evidence is
current — a UUID is only ever used, in the API layer's list routes, to stabilize presentation
ordering when even `ingested_at` ties exactly. Inactive source evidence (plan §D2/§G) is
excluded before selection is even attempted (step 0), so a cleared/invalidated reading can never
be picked as current.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    CapabilityAssessment,
    CapabilityMetric,
    CapabilityScore,
    CapabilityScoreAssessment,
    RecoveryReading,
)
from app.services.capability_db_compat import idempotent_insert
from app.services.capability_identity import deterministic_id

DEFAULT_COMPUTATION_METHOD = "latest_assessment_v1"

# One real entry, for the one pair of competing derivation methods that exists among Milestone
# 2's two activated metrics — not a general precedence framework. A direct-distance measurement
# (10K) carries less predictive uncertainty than a Riegel cross-prediction (5K), the same
# evidence-quality reasoning already used throughout this project's evidence-class grading.
SOURCE_PRECEDENCE_RULES: dict[frozenset[str], str] = {
    frozenset({"pace_from_10k_time_trial_v1", "riegel_threshold_pace_from_5k_v1"}): "pace_from_10k_time_trial_v1",
}


def is_source_evidence_active(db: Session, assessment: CapabilityAssessment) -> bool:
    """Whether the evidence an assessment cites still exists in a form that supports it, checked
    live at read/selection time rather than stored as mutable state. `BenchmarkResult` is
    immutable, so a benchmark-derived assessment is always active. A wearable-derived assessment
    is active only while its cited `RecoveryReading.vo2_max` is still non-null — the real
    `record_reading` code has no path that ever clears an existing value (plan §D2), so this is
    structurally always true today, but the check is real, not assumed."""
    if assessment.assessment_type != "wearable_derived":
        return True
    reading = db.get(RecoveryReading, assessment.recovery_reading_id)
    return reading is not None and reading.vo2_max is not None


@dataclass
class SelectionResult:
    status: str  # "resolved" | "ambiguous_evidence" | "no_current_evidence"
    assessment: Optional[CapabilityAssessment] = None
    competing_assessment_ids: list[str] = field(default_factory=list)


def select_current_assessment(db: Session, athlete_id: str, metric_id: str) -> SelectionResult:
    assessments = (
        db.query(CapabilityAssessment)
        .filter(CapabilityAssessment.athlete_id == athlete_id, CapabilityAssessment.metric_id == metric_id)
        .all()
    )
    active = [a for a in assessments if is_source_evidence_active(db, a)]
    if not active:
        return SelectionResult(status="no_current_evidence")

    max_recorded_at = max(a.recorded_at for a in active)
    tied = [a for a in active if a.recorded_at == max_recorded_at]
    if len(tied) == 1:
        return SelectionResult(status="resolved", assessment=tied[0])

    def _lineage_key(a: CapabilityAssessment) -> str:
        return a.derivation_method or a.assessment_type

    lineages = {_lineage_key(a) for a in tied}
    if len(lineages) == 1:
        winner = max(tied, key=lambda a: a.ingested_at)
        return SelectionResult(status="resolved", assessment=winner)

    preferred_key = SOURCE_PRECEDENCE_RULES.get(frozenset(lineages))
    if preferred_key is not None:
        preferred = [a for a in tied if _lineage_key(a) == preferred_key]
        if len(preferred) == 1:
            return SelectionResult(status="resolved", assessment=preferred[0])

    return SelectionResult(status="ambiguous_evidence", competing_assessment_ids=sorted(a.id for a in tied))


def get_score_lineage(db: Session, score: Optional[CapabilityScore]) -> tuple[list[str], list[dict]]:
    """Read-only lineage lookup: every `CapabilityAssessment` linked to `score` via
    `CapabilityScoreAssessment`, plus each assessment's own underlying source reference
    (whichever of `benchmark_result_id`/`recovery_reading_id`/`past_hyrox_result_id`/`workout_id`
    is set). Backs the full gap -> score -> assessment -> source lineage the API is required to
    expose (plan §A route 6/7). Deterministic order (`assessment_id` ascending) — never relies on
    row-insertion order."""
    if score is None:
        return [], []

    links = (
        db.query(CapabilityScoreAssessment)
        .filter(CapabilityScoreAssessment.score_id == score.id)
        .order_by(CapabilityScoreAssessment.assessment_id.asc())
        .all()
    )
    assessment_ids: list[str] = []
    source_references: list[dict] = []
    for link in links:
        assessment = db.get(CapabilityAssessment, link.assessment_id)
        if assessment is None:
            continue
        assessment_ids.append(assessment.id)
        source_id = (
            assessment.benchmark_result_id
            or assessment.recovery_reading_id
            or assessment.past_hyrox_result_id
            or assessment.workout_id
        )
        source_references.append({
            "assessment_id": assessment.id,
            "assessment_type": assessment.assessment_type,
            "source_id": source_id,
        })
    return assessment_ids, source_references


def compute_score_from_current_assessment(
    db: Session, athlete_id: str, metric_id: str, computation_method: str = DEFAULT_COMPUTATION_METHOD
) -> Optional[CapabilityScore]:
    """Returns None (writes nothing) when there is no single resolvable current assessment —
    `ambiguous_evidence` and `no_current_evidence` both mean no score can honestly be computed
    this round (plan §D4). Idempotent via a deterministic id built from the winning assessment's
    own id, so recomputing against unchanged evidence is a true no-op (plan §D5)."""
    selection = select_current_assessment(db, athlete_id, metric_id)
    if selection.status != "resolved":
        return None

    assessment = selection.assessment
    metric = db.get(CapabilityMetric, metric_id)
    score_id = deterministic_id("capability_scores", athlete_id, metric_id, assessment.id, computation_method)

    score_values = dict(
        id=score_id,
        athlete_id=athlete_id,
        metric_id=metric_id,
        value=assessment.raw_value,
        computation_method=computation_method,
        evidence_class=metric.evidence_class,
        computed_at=datetime.utcnow(),
    )
    score = idempotent_insert(db, CapabilityScore, score_values)

    link_id = deterministic_id("capability_score_assessments", score.id, assessment.id)
    link_values = dict(
        id=link_id, score_id=score.id, assessment_id=assessment.id, athlete_id=athlete_id, metric_id=metric_id
    )
    idempotent_insert(db, CapabilityScoreAssessment, link_values, conflict_columns=("score_id", "assessment_id"))

    return score
