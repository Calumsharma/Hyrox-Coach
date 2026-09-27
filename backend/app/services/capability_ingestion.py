"""Capability evidence ingestion — Program Engine v5 Milestone 2, plan §D2/§D3/§D6.

Two activated metrics only: `vo2max_wearable_ml_kg_min` (directly ingested wearable-derived
estimate, no formula applied) and `threshold_pace_riegel_sec_per_km` (derived from a real 5K or
10K `BenchmarkResult` via the existing, unmodified `app/services/pace.py` functions).

Ingestion never calls `app/services/pace.py::resolve_pace_profile` — that function reads the
mutable `Athlete.predicted_5k_seconds`/`current_10k_seconds` fields directly, exactly the
lineage problem Milestone 1B's precondition warned against. Only the pure
`predict_equivalent_time` function is reused here, applied to an immutable
`BenchmarkResult.raw_value`.

Every insert goes through `capability_db_compat.idempotent_insert` with a deterministic id
(`capability_identity.deterministic_id`) — see the plan's §D5 for why check-then-insert was
replaced with this.
"""

from __future__ import annotations

from datetime import datetime, time
from typing import Iterator, Optional, Tuple

from sqlalchemy.orm import Session

from app.models import BenchmarkResult, CapabilityAssessment, CapabilityMetric, RecoveryReading
from app.seed_data.benchmarks import FIVE_K_BENCHMARK_ID, TEN_K_BENCHMARK_ID
from app.services.capability_db_compat import idempotent_insert
from app.services.capability_identity import deterministic_id
from app.services.pace import FIVE_K_METERS, TEN_K_METERS, predict_equivalent_time

VO2MAX_METRIC_ID = "vo2max_wearable_ml_kg_min"
THRESHOLD_PACE_METRIC_ID = "threshold_pace_riegel_sec_per_km"
SUPPORTED_METRIC_IDS = (VO2MAX_METRIC_ID, THRESHOLD_PACE_METRIC_ID)


class UnsupportedMetricError(ValueError):
    """Raised for a metric_id outside Milestone 2's two activated metrics — never silently
    ignored, since expanding capability activation is a scope decision, not an accident."""


class UnsupportedBenchmarkError(ValueError):
    """Raised for a benchmark_id that isn't one of the two recognized 5K/10K definitions."""


def _enum_value(v):
    """Normalizes a value that may be a `str`-mixin enum member (freshly set in this session)
    or a plain string (freshly loaded from the database, since these columns are bare `String`,
    not a SQLAlchemy `Enum` type) to its plain string content, either way."""
    return getattr(v, "value", v)


def ingest_vo2max_from_recovery_reading(db: Session, recovery_reading: RecoveryReading) -> Optional[CapabilityAssessment]:
    """Directly ingested wearable-derived estimate — `derivation_method=NULL`, since this app
    applies no transformation. Idempotency key is `(recovery_reading_id, source_revision)`, not
    `(recovery_reading_id, raw_value)` — the fix for the `50 -> 51 -> 50` case (plan §D2/§D5):
    each genuine change to `RecoveryReading.vo2_max` bumps `vo2_max_updated_at`, which is what
    `source_revision` is built from, so a value that happens to repeat still gets a new,
    correctly-ordered assessment rather than being mistaken for the original.
    """
    if recovery_reading.vo2_max is None:
        return None

    metric = db.get(CapabilityMetric, VO2MAX_METRIC_ID)
    source_revision = (
        str(recovery_reading.vo2_max_updated_at)
        if recovery_reading.vo2_max_updated_at is not None
        else "unknown_historical"
    )
    assessment_id = deterministic_id(
        "capability_assessments", recovery_reading.athlete_id, VO2MAX_METRIC_ID, recovery_reading.id, source_revision
    )
    recorded_at = datetime.combine(recovery_reading.reading_date, time.min)
    provider_label = _enum_value(recovery_reading.vo2_max_source) or "unknown"

    values = dict(
        id=assessment_id,
        athlete_id=recovery_reading.athlete_id,
        metric_id=VO2MAX_METRIC_ID,
        raw_value=recovery_reading.vo2_max,
        derivation_method=None,
        assessment_type="wearable_derived",
        recovery_reading_id=recovery_reading.id,
        recorded_at=recorded_at,
        ingested_at=datetime.utcnow(),
        source_revision=source_revision,
        context_note=f"source_provider={provider_label}",
        evidence_class=metric.evidence_class,
    )
    return idempotent_insert(db, CapabilityAssessment, values)


def ingest_threshold_pace_from_benchmark_result(db: Session, benchmark_result: BenchmarkResult) -> CapabilityAssessment:
    """Two derivation paths: a 10K result is a pure unit conversion (no predictive formula,
    since 10K pace already IS this metric's underlying heuristic for threshold pace); a 5K
    result is a real Riegel cross-prediction. `BenchmarkResult` is immutable, so a given result
    can only ever produce one assessment for this metric — `source_revision` stays NULL.
    """
    if benchmark_result.benchmark_id == TEN_K_BENCHMARK_ID:
        derivation_method = "pace_from_10k_time_trial_v1"
        pace_sec_per_km = benchmark_result.raw_value / (TEN_K_METERS / 1000.0)
    elif benchmark_result.benchmark_id == FIVE_K_BENCHMARK_ID:
        derivation_method = "riegel_threshold_pace_from_5k_v1"
        ten_k_equivalent_seconds = predict_equivalent_time(benchmark_result.raw_value, FIVE_K_METERS, TEN_K_METERS)
        pace_sec_per_km = ten_k_equivalent_seconds / (TEN_K_METERS / 1000.0)
    else:
        raise UnsupportedBenchmarkError(f"{benchmark_result.benchmark_id!r} is not a recognized 5K/10K benchmark")

    metric = db.get(CapabilityMetric, THRESHOLD_PACE_METRIC_ID)
    assessment_id = deterministic_id(
        "capability_assessments", benchmark_result.athlete_id, THRESHOLD_PACE_METRIC_ID, benchmark_result.id
    )

    values = dict(
        id=assessment_id,
        athlete_id=benchmark_result.athlete_id,
        metric_id=THRESHOLD_PACE_METRIC_ID,
        raw_value=pace_sec_per_km,
        derivation_method=derivation_method,
        assessment_type="benchmark_result",
        benchmark_result_id=benchmark_result.id,
        recorded_at=benchmark_result.completed_at,
        ingested_at=datetime.utcnow(),
        source_revision=None,
        evidence_class=metric.evidence_class,
    )
    return idempotent_insert(db, CapabilityAssessment, values)


def eligible_source_snapshots(db: Session, athlete_id: str, metric_id: str) -> Iterator[Tuple[str, object, str]]:
    """Yields (source_kind, source_row, would_be_assessment_id) for every eligible source row
    for this athlete/metric, in deterministic `(measurement time, id)` order — regardless of
    whether it has already been ingested. Callers decide whether to ingest (recompute, §D6) or
    merely count (status, §D8); the same eligibility logic backs both, so "not yet ingested" is
    never a separately-maintained bookkeeping concept — it falls out of comparing this list
    against what already exists.
    """
    if metric_id == VO2MAX_METRIC_ID:
        readings = (
            db.query(RecoveryReading)
            .filter(RecoveryReading.athlete_id == athlete_id, RecoveryReading.vo2_max.isnot(None))
            .order_by(RecoveryReading.reading_date.asc(), RecoveryReading.id.asc())
            .all()
        )
        for reading in readings:
            source_revision = (
                str(reading.vo2_max_updated_at) if reading.vo2_max_updated_at is not None else "unknown_historical"
            )
            assessment_id = deterministic_id(
                "capability_assessments", athlete_id, metric_id, reading.id, source_revision
            )
            yield ("recovery_reading", reading, assessment_id)
    elif metric_id == THRESHOLD_PACE_METRIC_ID:
        results = (
            db.query(BenchmarkResult)
            .filter(
                BenchmarkResult.athlete_id == athlete_id,
                BenchmarkResult.benchmark_id.in_([FIVE_K_BENCHMARK_ID, TEN_K_BENCHMARK_ID]),
            )
            .order_by(BenchmarkResult.completed_at.asc(), BenchmarkResult.id.asc())
            .all()
        )
        for result in results:
            assessment_id = deterministic_id("capability_assessments", athlete_id, metric_id, result.id)
            yield ("benchmark_result", result, assessment_id)
    else:
        raise UnsupportedMetricError(metric_id)


def ingest_all_eligible(db: Session, athlete_id: str, metric_id: str) -> list[CapabilityAssessment]:
    """The real ingestion pass behind `POST /capabilities/recompute` (plan §D6). Processes every
    eligible source snapshot; an already-ingested revision is a true no-op at the database level
    (deterministic id + `ON CONFLICT DO NOTHING`), so this never creates a duplicate regardless
    of how many times it's called."""
    ingested = []
    for source_kind, source_row, _assessment_id in eligible_source_snapshots(db, athlete_id, metric_id):
        if source_kind == "recovery_reading":
            result = ingest_vo2max_from_recovery_reading(db, source_row)
        else:
            result = ingest_threshold_pace_from_benchmark_result(db, source_row)
        if result is not None:
            ingested.append(result)
    return ingested


def count_pending_source_snapshots(db: Session, athlete_id: str, metric_id: str) -> int:
    """Read-only: how many eligible source rows have not yet produced a matching
    `CapabilityAssessment`. Never inserts anything — backs `GET /capabilities/status`'s
    `recompute_required`/`pending_source_snapshot_count` fields (plan §D8)."""
    count = 0
    for _source_kind, _source_row, assessment_id in eligible_source_snapshots(db, athlete_id, metric_id):
        if db.get(CapabilityAssessment, assessment_id) is None:
            count += 1
    return count
