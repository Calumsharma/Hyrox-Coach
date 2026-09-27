"""Concurrency-safe idempotency via deterministic, content-addressed IDs — Program Engine v5
Milestone 2, plan §D5. Duplicate prevention is a database-level uniqueness guarantee
(`ON CONFLICT DO NOTHING` + deterministic id), not an application-level check-then-insert race.

Honest limitation, unchanged from the plan: SQLite's single-writer model means a genuinely
simultaneous multi-process write cannot be demonstrated here. The "interleaved" test below shows
two independent `Session` objects — unaware of each other's in-memory state — both attempting
the identical insert, which is what SQLite can actually exercise; it proves the dedup mechanism
by construction, not true multi-process simultaneity.
"""

from datetime import datetime

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db import Base
import app.models  # noqa: F401 — registers every model on Base.metadata
from app.models import (
    Athlete,
    CapabilityAssessment,
    CapabilityDefinition,
    CapabilityGap,
    CapabilityMetric,
    CapabilityScore,
    CapabilityScoreAssessment,
)
from app.services.capability_db_compat import compile_postgresql_statement, idempotent_insert
from app.services.capability_gap_service import compute_gap
from app.services.capability_identity import deterministic_id
from app.services.capability_ingestion import ingest_all_eligible
from app.services.capability_scoring import compute_score_from_current_assessment


def _athlete(db_session, email="idem@example.com"):
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


def _self_report_assessment(db_session, athlete, metric, raw_value, recorded_at):
    a = CapabilityAssessment(
        athlete_id=athlete.id, metric_id=metric.id, raw_value=raw_value, derivation_method=None,
        assessment_type="self_report", recorded_at=recorded_at, ingested_at=recorded_at,
        source_revision=None, evidence_class="coach_derived",
    )
    db_session.add(a)
    db_session.commit()
    return a


# --- Sequential duplicate recomputation ---

def test_sequential_duplicate_recomputation_creates_zero_new_rows(db_session):
    from app.models import BenchmarkDefinition, BenchmarkDefinitionMetric, BenchmarkResult
    from app.seed_data.benchmarks import TEN_K_BENCHMARK_ID

    athlete = _athlete(db_session)
    metric = _metric(db_session)
    db_session.add(BenchmarkDefinition(id=TEN_K_BENCHMARK_ID, name="10K Time Trial", protocol_description="", unit="sec", evidence_class="coach_derived"))
    db_session.add(BenchmarkDefinitionMetric(benchmark_id=TEN_K_BENCHMARK_ID, metric_id=metric.id))
    db_session.commit()
    result = BenchmarkResult(athlete_id=athlete.id, benchmark_id=TEN_K_BENCHMARK_ID, completed_at=datetime(2026, 8, 1), raw_value=2400.0, context={}, notes="")
    db_session.add(result)
    db_session.commit()

    ingest_all_eligible(db_session, athlete.id, metric.id)
    score1 = compute_score_from_current_assessment(db_session, athlete.id, metric.id)
    gap1 = compute_gap(db_session, athlete.id, metric.id, score1)
    db_session.commit()

    assessment_count_1 = db_session.query(CapabilityAssessment).count()
    score_count_1 = db_session.query(CapabilityScore).count()
    link_count_1 = db_session.query(CapabilityScoreAssessment).count()
    gap_count_1 = db_session.query(CapabilityGap).count()

    # Second call, no new evidence — must be a true no-op across all four tables.
    ingest_all_eligible(db_session, athlete.id, metric.id)
    score2 = compute_score_from_current_assessment(db_session, athlete.id, metric.id)
    gap2 = compute_gap(db_session, athlete.id, metric.id, score2)
    db_session.commit()

    assert db_session.query(CapabilityAssessment).count() == assessment_count_1
    assert db_session.query(CapabilityScore).count() == score_count_1
    assert db_session.query(CapabilityScoreAssessment).count() == link_count_1
    assert db_session.query(CapabilityGap).count() == gap_count_1
    assert score2.id == score1.id
    assert gap2.id == gap1.id


# --- Interleaved-transaction duplicate recomputation ---

def _new_file_session(db_path):
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return sessionmaker(bind=engine)()


def test_interleaved_sessions_attempting_same_insert_produce_exactly_one_row(tmp_path):
    db_path = tmp_path / "idempotency.db"
    setup_engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=setup_engine)
    setup_engine.dispose()

    session_a = _new_file_session(db_path)
    session_b = _new_file_session(db_path)
    try:
        athlete = _athlete(session_a, email="interleaved@example.com")
        metric = _metric(session_a)
        session_b.expire_all()  # force session_b to see session_a's committed rows fresh

        assessment_id = deterministic_id("capability_assessments", athlete.id, metric.id, "fixed-marker")
        values = dict(
            id=assessment_id, athlete_id=athlete.id, metric_id=metric.id, raw_value=42.0,
            derivation_method=None, assessment_type="self_report",
            recorded_at=datetime(2026, 9, 1), ingested_at=datetime(2026, 9, 1),
            source_revision=None, evidence_class="coach_derived",
        )

        # Neither session knows about the other's attempt — both call idempotent_insert with the
        # identical deterministic id, simulating two independent, unaware callers. Each session
        # commits its own attempt immediately afterward — idempotent_insert itself never commits
        # (point 2), so each CALLER is responsible for concluding its own transaction, exactly as
        # a real request handler would after its recompute workflow finishes.
        row_a = idempotent_insert(session_a, CapabilityAssessment, values)
        session_a.commit()
        row_b = idempotent_insert(session_b, CapabilityAssessment, values)
        session_b.commit()

        assert row_a.id == row_b.id == assessment_id
        count = session_a.query(CapabilityAssessment).filter(CapabilityAssessment.id == assessment_id).count()
        assert count == 1
    finally:
        session_a.close()
        session_b.close()


# --- New evidence, unchanged numeric value, genuinely new source revision ---

def test_new_source_revision_with_unchanged_value_creates_a_new_row(db_session):
    from app.models import RecoveryReading
    from app.models.enums import WearableProvider
    from app.services.capability_ingestion import ingest_vo2max_from_recovery_reading
    from app.services.recovery_engine import record_reading
    from datetime import date

    athlete = _athlete(db_session)
    _metric(db_session, metric_id="vo2max_wearable_ml_kg_min", capability_id="aerobic_capacity")

    reading = record_reading(db_session, athlete.id, date(2026, 8, 1), WearableProvider.APPLE_HEALTH, vo2_max=50.0)
    a1 = ingest_vo2max_from_recovery_reading(db_session, reading)

    reading = record_reading(db_session, athlete.id, date(2026, 8, 2), WearableProvider.APPLE_HEALTH, vo2_max=50.0)
    reading2 = db_session.query(RecoveryReading).filter(RecoveryReading.athlete_id == athlete.id, RecoveryReading.reading_date == date(2026, 8, 2)).first()
    a2 = ingest_vo2max_from_recovery_reading(db_session, reading2)

    assert a1.id != a2.id
    assert a1.raw_value == a2.raw_value == 50.0


# --- Changed score producing a new, provenance-linked gap, even with unchanged classification ---

def test_changed_score_produces_new_gap_even_with_unchanged_classification(db_session):
    athlete = _athlete(db_session)
    metric = _metric(db_session)

    a1 = _self_report_assessment(db_session, athlete, metric, 300.0, datetime(2026, 8, 1))
    score1 = compute_score_from_current_assessment(db_session, athlete.id, metric.id)
    gap1 = compute_gap(db_session, athlete.id, metric.id, score1)
    assert gap1.classification == "unclassified"
    assert gap1.confidence == "none"

    # New, later evidence — a genuinely different score (new based_on_score_id), even though the
    # production classification/confidence outcome is identical ("unclassified"/"none").
    a2 = _self_report_assessment(db_session, athlete, metric, 310.0, datetime(2026, 8, 15))
    score2 = compute_score_from_current_assessment(db_session, athlete.id, metric.id)
    gap2 = compute_gap(db_session, athlete.id, metric.id, score2)

    assert score2.id != score1.id
    assert gap2.id != gap1.id
    assert gap2.based_on_score_id != gap1.based_on_score_id
    assert gap2.classification == gap1.classification == "unclassified"
    assert gap2.confidence == gap1.confidence == "none"


# --- PostgreSQL statement path: compile-only, never a live PostgreSQL connection ---

def test_postgresql_statement_compiles_with_on_conflict_clause():
    values = dict(
        id="pg-compile-test", athlete_id="a", metric_id="m", raw_value=1.0, derivation_method=None,
        assessment_type="self_report", recorded_at=datetime(2026, 9, 1), ingested_at=datetime(2026, 9, 1),
        source_revision=None, evidence_class="coach_derived",
    )
    compiled_sql = compile_postgresql_statement(CapabilityAssessment, values)
    assert "ON CONFLICT" in compiled_sql
    assert "capability_assessments" in compiled_sql


# --- idempotent_insert never commits the caller's transaction (point 2) ---

def test_idempotent_insert_does_not_commit_callers_transaction(db_session):
    athlete = _athlete(db_session)
    metric = _metric(db_session)
    assessment_id = deterministic_id("capability_assessments", athlete.id, metric.id, "no-commit-marker")
    values = dict(
        id=assessment_id, athlete_id=athlete.id, metric_id=metric.id, raw_value=1.0, derivation_method=None,
        assessment_type="self_report", recorded_at=datetime(2026, 9, 1), ingested_at=datetime(2026, 9, 1),
        source_revision=None, evidence_class="coach_derived",
    )

    row = idempotent_insert(db_session, CapabilityAssessment, values)
    assert row is not None  # flushed and visible within this same transaction

    # Rolling back — rather than committing — must discard it entirely, proving idempotent_insert
    # itself never committed on the caller's behalf.
    db_session.rollback()
    assert db_session.query(CapabilityAssessment).filter(CapabilityAssessment.id == assessment_id).first() is None


# --- A forced failure mid-recompute leaves no partial chain (point 2) ---

def test_forced_failure_between_scoring_and_gap_creation_leaves_no_partial_chain(db_session, monkeypatch):
    """Simulates exactly the failure mode the recompute route's try/rollback/raise is meant to
    guard against: ingestion and scoring succeed, then something raises before the gap is
    created. The caller (here, standing in for the route) rolls back — proving the whole
    recomputation reverts as one unit, not just the step that failed."""
    from app.models import BenchmarkDefinition, BenchmarkDefinitionMetric, BenchmarkResult
    from app.seed_data.benchmarks import TEN_K_BENCHMARK_ID
    import app.services.capability_gap_service as gap_service_module

    athlete = _athlete(db_session)
    metric = _metric(db_session)
    db_session.add(BenchmarkDefinition(id=TEN_K_BENCHMARK_ID, name="10K Time Trial", protocol_description="", unit="sec", evidence_class="coach_derived"))
    db_session.add(BenchmarkDefinitionMetric(benchmark_id=TEN_K_BENCHMARK_ID, metric_id=metric.id))
    db_session.commit()
    result = BenchmarkResult(athlete_id=athlete.id, benchmark_id=TEN_K_BENCHMARK_ID, completed_at=datetime(2026, 8, 1), raw_value=2400.0, context={}, notes="")
    db_session.add(result)
    db_session.commit()

    def _boom(*args, **kwargs):
        raise RuntimeError("forced failure between scoring and gap creation")

    monkeypatch.setattr(gap_service_module, "compute_gap", _boom)

    with pytest.raises(RuntimeError):
        # Mirrors the route's own try/except-rollback-reraise shape exactly.
        try:
            ingest_all_eligible(db_session, athlete.id, metric.id)
            score = compute_score_from_current_assessment(db_session, athlete.id, metric.id)
            gap_service_module.compute_gap(db_session, athlete.id, metric.id, score)
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    # The whole recomputation reverted — including the assessment and score ingested/computed
    # earlier in this same failed call, not just the gap step that actually raised.
    assert db_session.query(CapabilityAssessment).count() == 0
    assert db_session.query(CapabilityScore).count() == 0
    assert db_session.query(CapabilityScoreAssessment).count() == 0
    assert db_session.query(CapabilityGap).count() == 0
