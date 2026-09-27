from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

from app.services.capability_ingestion import SUPPORTED_METRIC_IDS

__all__ = ["SUPPORTED_METRIC_IDS"]


class BenchmarkDefinitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    protocol_description: str
    unit: str
    evidence_class: str
    metric_ids: list[str] = []


class BenchmarkContextCreate(BaseModel):
    """Program Engine v5 Milestone 2, plan §H — the corrected context shape (test_type and
    surface are separate concepts, not conflated). The first four fields are required at this
    API boundary; only `notes` is optional."""

    test_type: Literal["time_trial", "official_race"]
    surface: Literal["track", "road", "treadmill", "other"]
    elapsed_time_basis: Literal["watch_time", "official_timing", "video_verified"]
    distance_verification: Literal[
        "certified_course", "measured_track", "calibrated_treadmill", "gps_measured", "other"
    ]
    notes: Optional[str] = None


class BenchmarkResultCreate(BaseModel):
    """`athlete_id` is deliberately not a field here — structurally absent, so there is nothing
    in the payload a client could use to submit a result on another athlete's behalf. The
    server always takes `athlete_id` from `get_current_athlete()`."""

    benchmark_id: str
    completed_at: datetime
    raw_value: float
    context: BenchmarkContextCreate


class BenchmarkResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    benchmark_id: str
    completed_at: datetime
    raw_value: float
    context: dict
    notes: str


class RecomputeRequest(BaseModel):
    metric_id: str


class CapabilityAssessmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    metric_id: str
    raw_value: float
    derivation_method: Optional[str] = None
    assessment_type: str
    recorded_at: datetime
    ingested_at: datetime
    source_revision: Optional[str] = None
    context_note: Optional[str] = None
    evidence_class: str
    is_currently_selected: bool = False
    source_evidence_active: bool = True


class CapabilityScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    metric_id: str
    value: float
    computation_method: str
    evidence_class: str
    computed_at: datetime
    is_current: bool = False


class SourceReference(BaseModel):
    """One assessment's underlying source reference — whichever of `benchmark_result_id`/
    `recovery_reading_id`/`past_hyrox_result_id`/`workout_id` is actually set on it."""

    assessment_id: str
    assessment_type: str
    source_id: Optional[str] = None


class CapabilityGapRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    metric_id: str
    classification: str
    confidence: str
    based_on_score_id: str
    band_policy_id: Optional[str] = None
    reasoning: str
    computed_at: datetime
    is_current: bool = False
    # Complete lineage: gap -> score (based_on_score_id, above) -> assessment(s) -> each
    # assessment's underlying source reference. Populated by the route, not derivable from the
    # ORM object alone (requires a join through CapabilityScoreAssessment).
    assessment_ids: list[str] = []
    source_references: list[SourceReference] = []


class RecomputeResponse(BaseModel):
    status: str  # "ok" | "ambiguous_evidence" | "no_current_evidence"
    gap: Optional[CapabilityGapRead] = None
    competing_assessment_ids: list[str] = []


class CapabilityStatusRead(BaseModel):
    """The consolidated, read-only status contract — plan §A route 7 / §D8. Distinguishes
    current vs. stale-pending-recompute vs. no-current-evidence vs. ambiguous, so the caller
    never has to cross-reference the list routes by hand."""

    state: str  # "current" | "recompute_required" | "no_current_evidence" | "ambiguous_evidence"
    current_assessment: Optional[CapabilityAssessmentRead] = None
    current_score: Optional[CapabilityScoreRead] = None
    current_gap: Optional[CapabilityGapRead] = None
    recompute_required: bool = False
    pending_source_snapshot_count: int = 0
    current_as_of: Optional[str] = None
    status_reason: str = ""
    ambiguous_candidates: list[str] = []
    inactive_source_evidence: list[str] = []
    provenance: dict = {}
