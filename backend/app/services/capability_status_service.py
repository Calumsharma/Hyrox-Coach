"""Read-only capability status/freshness computation — Program Engine v5 Milestone 2, plan §D8.

Backs `GET /capabilities/status`. Never inserts, updates, or deletes anything — every check here
is a read against already-ingested data plus a "would this be new" count against not-yet-ingested
source rows (via `capability_ingestion.count_pending_source_snapshots`, which itself only reads),
never an actual ingestion. A dedicated test asserts row counts are unchanged across all four
capability tables (including the `CapabilityScoreAssessment` lineage table) after calling this,
regardless of state.

**Corrected (independent review, first pass): `state="current"` requires a verified, complete
chain from the uniquely selected active assessment** — not merely "some gap exists somewhere for
this metric." Resolve the current assessment first, then look up ONLY the score/gap that
specifically link back to that exact assessment; if either is missing, the state is
`recompute_required`, never `current`.

**Corrected (independent review, second pass): pending source snapshots are checked BEFORE
assessment selection, per the approved plan §D8 — not after.** If any eligible source snapshot
hasn't been ingested yet, `state` is unconditionally `"recompute_required"`, even when zero
`CapabilityAssessment` rows exist yet, and even when the already-ingested evidence would
otherwise resolve as ambiguous. Only once `pending == 0` does the service choose between
`current`, `no_current_evidence`, and `ambiguous_evidence`. When pending evidence exists, this
returns the STORED, potentially-stale chain (the most recently computed gap and what it traces
back to, independent of whether that assessment would still be selected under the tie-break
ladder) if one exists, or leaves all three `current_*` fields null if no chain has ever been
computed — the status reason names which case applies either way.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models import CapabilityAssessment, CapabilityGap, CapabilityScore, CapabilityScoreAssessment
from app.services.capability_ingestion import count_pending_source_snapshots
from app.services.capability_scoring import is_source_evidence_active, select_current_assessment


@dataclass
class CapabilityStatus:
    state: str  # "current" | "recompute_required" | "no_current_evidence" | "ambiguous_evidence"
    current_assessment: Optional[CapabilityAssessment] = None
    current_score: Optional[CapabilityScore] = None
    current_gap: Optional[CapabilityGap] = None
    recompute_required: bool = False
    pending_source_snapshot_count: int = 0
    current_as_of: Optional[str] = None
    status_reason: str = ""
    ambiguous_candidates: list[str] = field(default_factory=list)
    inactive_source_evidence: list[str] = field(default_factory=list)
    provenance: dict = field(default_factory=dict)


def _provenance(assessment, score, gap) -> dict:
    return {
        "assessment_ids": [assessment.id] if assessment else [],
        "score_id": score.id if score else None,
        "gap_id": gap.id if gap else None,
    }


def _find_chain_for_assessment(
    db: Session, athlete_id: str, metric_id: str, assessment: CapabilityAssessment
) -> Tuple[Optional[CapabilityScore], Optional[CapabilityGap]]:
    """The score and gap that specifically trace back to THIS exact assessment (via
    `CapabilityScoreAssessment`, then `CapabilityGap.based_on_score_id`) — never "the latest gap
    for this metric, whatever it happens to be based on." Either or both may be `None` if
    recomputation hasn't caught up with this assessment yet."""
    link = (
        db.query(CapabilityScoreAssessment)
        .filter(
            CapabilityScoreAssessment.assessment_id == assessment.id,
            CapabilityScoreAssessment.athlete_id == athlete_id,
            CapabilityScoreAssessment.metric_id == metric_id,
        )
        .first()
    )
    if link is None:
        return None, None

    score = db.get(CapabilityScore, link.score_id)
    if score is None:
        return None, None

    gap = (
        db.query(CapabilityGap)
        .filter(
            CapabilityGap.based_on_score_id == score.id,
            CapabilityGap.athlete_id == athlete_id,
            CapabilityGap.metric_id == metric_id,
        )
        .order_by(CapabilityGap.computed_at.desc(), CapabilityGap.id.desc())
        .first()
    )
    return score, gap


def _latest_stored_chain(
    db: Session, athlete_id: str, metric_id: str
) -> Tuple[Optional[CapabilityAssessment], Optional[CapabilityScore], Optional[CapabilityGap]]:
    """The most recently computed gap for this athlete/metric, plus the score and assessment it
    traces back to — a STORED, potentially-stale chain, independent of `select_current_assessment`
    (which reasons about currently-active evidence, not "whatever was last actually computed").
    Used only when pending source snapshots mean fresh selection would be premature: this is the
    result of the last real recompute, honestly labeled as possibly stale, not a fresh re-derivation."""
    gap = (
        db.query(CapabilityGap)
        .filter(CapabilityGap.athlete_id == athlete_id, CapabilityGap.metric_id == metric_id)
        .order_by(CapabilityGap.computed_at.desc(), CapabilityGap.id.desc())
        .first()
    )
    if gap is None:
        return None, None, None

    score = db.get(CapabilityScore, gap.based_on_score_id)
    assessment = None
    if score is not None:
        link = (
            db.query(CapabilityScoreAssessment)
            .filter(CapabilityScoreAssessment.score_id == score.id)
            .first()
        )
        if link is not None:
            assessment = db.get(CapabilityAssessment, link.assessment_id)
    return assessment, score, gap


def compute_status(db: Session, athlete_id: str, metric_id: str) -> CapabilityStatus:
    all_assessments = (
        db.query(CapabilityAssessment)
        .filter(CapabilityAssessment.athlete_id == athlete_id, CapabilityAssessment.metric_id == metric_id)
        .all()
    )
    inactive_ids = [a.id for a in all_assessments if not is_source_evidence_active(db, a)]
    pending = count_pending_source_snapshots(db, athlete_id, metric_id)

    # Plan §D8: pending source snapshots are evaluated FIRST, before any assessment selection —
    # this applies even when zero assessments have ever been ingested, and even when the
    # already-ingested evidence would otherwise resolve as ambiguous. Only once pending == 0 does
    # the service choose between current/no_current_evidence/ambiguous_evidence below.
    if pending > 0:
        assessment, score, gap = _latest_stored_chain(db, athlete_id, metric_id)
        if gap is not None:
            reason = (
                f"{pending} source snapshot(s) not yet ingested — call POST /capabilities/recompute. "
                "Showing the previously computed result, which may now be stale."
            )
        else:
            reason = f"{pending} source snapshot(s) not yet ingested — call POST /capabilities/recompute. No previous result exists yet."
        return CapabilityStatus(
            state="recompute_required",
            current_assessment=assessment,
            current_score=score,
            current_gap=gap,
            recompute_required=True,
            pending_source_snapshot_count=pending,
            current_as_of=assessment.recorded_at.isoformat() if assessment else None,
            status_reason=reason,
            inactive_source_evidence=inactive_ids,
            provenance=_provenance(assessment, score, gap),
        )

    # pending == 0 from here on — safe to choose between current / no_current_evidence / ambiguous.
    selection = select_current_assessment(db, athlete_id, metric_id)

    # Ambiguous or no-evidence: never label any historical chain as current — all three
    # current_* fields stay null, exactly as specified.
    if selection.status == "ambiguous_evidence":
        return CapabilityStatus(
            state="ambiguous_evidence",
            pending_source_snapshot_count=0,
            ambiguous_candidates=selection.competing_assessment_ids,
            status_reason="Multiple assessments tie with no justified precedence rule.",
            inactive_source_evidence=inactive_ids,
            provenance=_provenance(None, None, None),
        )

    if selection.status == "no_current_evidence":
        return CapabilityStatus(
            state="no_current_evidence",
            pending_source_snapshot_count=0,
            status_reason="No active source evidence exists for this metric.",
            inactive_source_evidence=inactive_ids,
            provenance=_provenance(None, None, None),
        )

    # Resolved: exactly one active assessment is currently selected. "current" requires its
    # complete chain (score + lineage link + gap) to actually exist — not just that SOME gap
    # exists for this metric.
    assessment = selection.assessment
    score, gap = _find_chain_for_assessment(db, athlete_id, metric_id, assessment)

    if score is None or gap is None:
        return CapabilityStatus(
            state="recompute_required",
            current_assessment=assessment,
            current_score=score,
            current_gap=gap,
            recompute_required=True,
            pending_source_snapshot_count=0,
            current_as_of=assessment.recorded_at.isoformat(),
            status_reason="The currently selected assessment has no corresponding score/gap yet — call POST /capabilities/recompute.",
            inactive_source_evidence=inactive_ids,
            provenance=_provenance(assessment, score, gap),
        )

    return CapabilityStatus(
        state="current",
        current_assessment=assessment,
        current_score=score,
        current_gap=gap,
        current_as_of=assessment.recorded_at.isoformat(),
        status_reason="Current evidence is fully ingested and reflected in the latest gap.",
        inactive_source_evidence=inactive_ids,
        provenance=_provenance(assessment, score, gap),
    )
