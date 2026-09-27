from __future__ import annotations

import math

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_athlete
from app.db import get_db
from app.models import (
    Athlete,
    BenchmarkDefinition,
    BenchmarkDefinitionMetric,
    BenchmarkResult,
    CapabilityAssessment,
    CapabilityGap,
    CapabilityScore,
)
from app.schemas.capability import (
    BenchmarkDefinitionRead,
    BenchmarkResultCreate,
    BenchmarkResultRead,
    CapabilityAssessmentRead,
    CapabilityGapRead,
    CapabilityScoreRead,
    CapabilityStatusRead,
    RecomputeRequest,
    RecomputeResponse,
    SourceReference,
    SUPPORTED_METRIC_IDS,
)
from app.services.capability_gap_service import compute_gap
from app.services.capability_ingestion import FIVE_K_BENCHMARK_ID, TEN_K_BENCHMARK_ID, ingest_all_eligible
from app.services.capability_scoring import (
    compute_score_from_current_assessment,
    get_score_lineage,
    is_source_evidence_active,
    select_current_assessment,
)
from app.services.capability_status_service import compute_status

router = APIRouter(prefix="/capabilities", tags=["capabilities"])

_SUPPORTED_BENCHMARK_IDS = {FIVE_K_BENCHMARK_ID, TEN_K_BENCHMARK_ID}


def _require_supported_metric(metric_id: str) -> None:
    if metric_id not in SUPPORTED_METRIC_IDS:
        raise HTTPException(status_code=400, detail=f"Unsupported metric_id {metric_id!r}")


def _gap_read_with_lineage(db: Session, gap: CapabilityGap, *, is_current: bool = False) -> CapabilityGapRead:
    """Builds a `CapabilityGapRead` with the full gap -> score -> assessment -> source lineage
    populated (point 1's "complete lineage" requirement) — never left at the ORM-only fields."""
    read = CapabilityGapRead.model_validate(gap)
    read.is_current = is_current
    score = db.get(CapabilityScore, gap.based_on_score_id)
    assessment_ids, source_references = get_score_lineage(db, score)
    read.assessment_ids = assessment_ids
    read.source_references = [SourceReference(**ref) for ref in source_references]
    return read


# All seven routes require authentication (`get_current_athlete`), per the approved plan — this
# includes `benchmark-definitions`, even though its data is global reference content rather than
# athlete-scoped, since the plan specifies all seven as authenticated.
@router.get("/benchmark-definitions", response_model=list[BenchmarkDefinitionRead])
def list_benchmark_definitions(
    athlete: Athlete = Depends(get_current_athlete),
    db: Session = Depends(get_db),
):
    definitions = (
        db.query(BenchmarkDefinition)
        .filter(BenchmarkDefinition.id.in_(_SUPPORTED_BENCHMARK_IDS))
        .order_by(BenchmarkDefinition.id.asc())
        .all()
    )
    result = []
    for definition in definitions:
        read = BenchmarkDefinitionRead.model_validate(definition)
        links = (
            db.query(BenchmarkDefinitionMetric)
            .filter(BenchmarkDefinitionMetric.benchmark_id == definition.id)
            .order_by(BenchmarkDefinitionMetric.metric_id.asc())
            .all()
        )
        read.metric_ids = [link.metric_id for link in links]
        result.append(read)
    return result


@router.post("/benchmark-results", response_model=BenchmarkResultRead, status_code=status.HTTP_201_CREATED)
def submit_benchmark_result(
    payload: BenchmarkResultCreate,
    athlete: Athlete = Depends(get_current_athlete),
    db: Session = Depends(get_db),
):
    if payload.benchmark_id not in _SUPPORTED_BENCHMARK_IDS:
        raise HTTPException(status_code=400, detail=f"Unsupported benchmark_id {payload.benchmark_id!r}")
    if not math.isfinite(payload.raw_value) or payload.raw_value <= 0:
        raise HTTPException(status_code=400, detail="raw_value must be a finite, positive number")

    definition = db.get(BenchmarkDefinition, payload.benchmark_id)
    if definition is None or definition.unit != "sec":
        raise HTTPException(status_code=400, detail="Benchmark definition is not recognized or has an unexpected unit")

    link = (
        db.query(BenchmarkDefinitionMetric)
        .filter(BenchmarkDefinitionMetric.benchmark_id == payload.benchmark_id)
        .first()
    )
    if link is None:
        raise HTTPException(status_code=400, detail="Benchmark definition has no linked capability metric")

    result = BenchmarkResult(
        athlete_id=athlete.id,
        benchmark_id=payload.benchmark_id,
        completed_at=payload.completed_at,
        raw_value=payload.raw_value,
        context=payload.context.model_dump(exclude_none=True),
        notes="",
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


@router.post("/recompute", response_model=RecomputeResponse)
def recompute(
    payload: RecomputeRequest,
    athlete: Athlete = Depends(get_current_athlete),
    db: Session = Depends(get_db),
):
    """Single outer transaction covering ingestion, scoring, lineage and gap creation (point 2).
    Every step below (`ingest_all_eligible`, `compute_score_from_current_assessment`,
    `compute_gap`) uses `idempotent_insert`, which flushes but never commits — this route is the
    one place that commits, once, after everything succeeds. Any exception rolls back the entire
    recomputation, including assessments ingested earlier in this same call, so a genuine failure
    can never leave a partial assessment/score/lineage/gap chain behind."""
    _require_supported_metric(payload.metric_id)

    try:
        ingest_all_eligible(db, athlete.id, payload.metric_id)
        selection = select_current_assessment(db, athlete.id, payload.metric_id)

        if selection.status == "ambiguous_evidence":
            db.commit()
            return RecomputeResponse(status="ambiguous_evidence", competing_assessment_ids=selection.competing_assessment_ids)
        if selection.status == "no_current_evidence":
            db.commit()
            return RecomputeResponse(status="no_current_evidence")

        score = compute_score_from_current_assessment(db, athlete.id, payload.metric_id)
        gap = compute_gap(db, athlete.id, payload.metric_id, score)
        db.commit()
    except Exception:
        db.rollback()
        raise

    gap_read = _gap_read_with_lineage(db, gap, is_current=True) if gap is not None else None
    return RecomputeResponse(status="ok", gap=gap_read)


@router.get("/assessments", response_model=list[CapabilityAssessmentRead])
def list_assessments(
    metric_id: str,
    athlete: Athlete = Depends(get_current_athlete),
    db: Session = Depends(get_db),
):
    _require_supported_metric(metric_id)

    assessments = (
        db.query(CapabilityAssessment)
        .filter(CapabilityAssessment.athlete_id == athlete.id, CapabilityAssessment.metric_id == metric_id)
        .order_by(
            CapabilityAssessment.recorded_at.desc(),
            CapabilityAssessment.ingested_at.desc(),
            CapabilityAssessment.id.desc(),
        )
        .all()
    )
    selection = select_current_assessment(db, athlete.id, metric_id)
    selected_id = selection.assessment.id if selection.status == "resolved" else None

    result = []
    for a in assessments:
        read = CapabilityAssessmentRead.model_validate(a)
        read.is_currently_selected = a.id == selected_id
        read.source_evidence_active = is_source_evidence_active(db, a)
        result.append(read)
    return result


@router.get("/scores", response_model=list[CapabilityScoreRead])
def list_scores(
    metric_id: str,
    athlete: Athlete = Depends(get_current_athlete),
    db: Session = Depends(get_db),
):
    _require_supported_metric(metric_id)

    scores = (
        db.query(CapabilityScore)
        .filter(CapabilityScore.athlete_id == athlete.id, CapabilityScore.metric_id == metric_id)
        .order_by(CapabilityScore.computed_at.desc(), CapabilityScore.id.desc())
        .all()
    )
    current = compute_status(db, athlete.id, metric_id)
    current_id = current.current_score.id if current.current_score else None

    result = []
    for s in scores:
        read = CapabilityScoreRead.model_validate(s)
        read.is_current = s.id == current_id
        result.append(read)
    return result


@router.get("/gaps", response_model=list[CapabilityGapRead])
def list_gaps(
    metric_id: str,
    athlete: Athlete = Depends(get_current_athlete),
    db: Session = Depends(get_db),
):
    _require_supported_metric(metric_id)

    gaps = (
        db.query(CapabilityGap)
        .filter(CapabilityGap.athlete_id == athlete.id, CapabilityGap.metric_id == metric_id)
        .order_by(CapabilityGap.computed_at.desc(), CapabilityGap.id.desc())
        .all()
    )
    current = compute_status(db, athlete.id, metric_id)
    current_id = current.current_gap.id if current.current_gap else None

    return [_gap_read_with_lineage(db, g, is_current=(g.id == current_id)) for g in gaps]


@router.get("/status", response_model=CapabilityStatusRead)
def get_status(
    metric_id: str,
    athlete: Athlete = Depends(get_current_athlete),
    db: Session = Depends(get_db),
):
    _require_supported_metric(metric_id)

    result = compute_status(db, athlete.id, metric_id)

    current_assessment_read = None
    if result.current_assessment:
        current_assessment_read = CapabilityAssessmentRead.model_validate(result.current_assessment)
        # This IS the currently selected, active assessment by construction — never leave the
        # Pydantic defaults (False/True) standing in for what compute_status already determined.
        current_assessment_read.is_currently_selected = True
        current_assessment_read.source_evidence_active = True

    current_score_read = None
    if result.current_score:
        current_score_read = CapabilityScoreRead.model_validate(result.current_score)
        current_score_read.is_current = True

    current_gap_read = None
    if result.current_gap:
        current_gap_read = _gap_read_with_lineage(db, result.current_gap, is_current=True)

    return CapabilityStatusRead(
        state=result.state,
        current_assessment=current_assessment_read,
        current_score=current_score_read,
        current_gap=current_gap_read,
        recompute_required=result.recompute_required,
        pending_source_snapshot_count=result.pending_source_snapshot_count,
        current_as_of=result.current_as_of,
        status_reason=result.status_reason,
        ambiguous_candidates=result.ambiguous_candidates,
        inactive_source_evidence=result.inactive_source_evidence,
        provenance=result.provenance,
    )
