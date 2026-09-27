"""Read-only capability status/freshness — Program Engine v5 Milestone 2, plan §D8. Every check
here proves `compute_status` never writes anything, and correctly distinguishes current vs.
pending-recompute vs. no-current-evidence vs. ambiguous."""

from datetime import date, datetime

import pytest

from app.models import (
    Athlete,
    BenchmarkDefinition,
    BenchmarkDefinitionMetric,
    BenchmarkResult,
    CapabilityAssessment,
    CapabilityDefinition,
    CapabilityGap,
    CapabilityMetric,
    CapabilityScore,
    CapabilityScoreAssessment,
    RecoveryReading,
)
from app.models.enums import WearableProvider
from app.seed_data.benchmarks import TEN_K_BENCHMARK_ID
from app.services.capability_gap_service import compute_gap
from app.services.capability_ingestion import THRESHOLD_PACE_METRIC_ID, VO2MAX_METRIC_ID, ingest_all_eligible
from app.services.capability_ingestion import ingest_vo2max_from_recovery_reading
from app.services.capability_scoring import compute_score_from_current_assessment
from app.services.capability_status_service import compute_status
from app.services.recovery_engine import record_reading


def _athlete(db_session, email="status@example.com"):
    a = Athlete(email=email)
    db_session.add(a)
    db_session.commit()
    return a


def _threshold_pace_setup(db_session, athlete):
    db_session.add(CapabilityDefinition(id="threshold_race_pace", name="Threshold & Race Pace", description="", measurement_hint=""))
    db_session.commit()
    metric = CapabilityMetric(
        id=THRESHOLD_PACE_METRIC_ID, capability_id="threshold_race_pace", station=None, unit="sec_per_km",
        higher_is_better=False, evidence_class="coach_derived", description="",
    )
    db_session.add(metric)
    db_session.add(BenchmarkDefinition(id=TEN_K_BENCHMARK_ID, name="10K Time Trial", protocol_description="", unit="sec", evidence_class="coach_derived"))
    db_session.commit()
    db_session.add(BenchmarkDefinitionMetric(benchmark_id=TEN_K_BENCHMARK_ID, metric_id=THRESHOLD_PACE_METRIC_ID))
    db_session.commit()
    return metric


def _vo2max_setup(db_session):
    db_session.add(CapabilityDefinition(id="aerobic_capacity", name="Aerobic Capacity", description="", measurement_hint=""))
    db_session.commit()
    metric = CapabilityMetric(
        id=VO2MAX_METRIC_ID, capability_id="aerobic_capacity", station=None, unit="ml_kg_min",
        higher_is_better=True, evidence_class="research_supported", description="",
    )
    db_session.add(metric)
    db_session.commit()
    return metric


def _all_table_counts(db_session):
    # All four capability tables (point 6) — CapabilityScoreAssessment is the lineage table and
    # was previously omitted from this "zero-write" check.
    return (
        db_session.query(CapabilityAssessment).count(),
        db_session.query(CapabilityScore).count(),
        db_session.query(CapabilityScoreAssessment).count(),
        db_session.query(CapabilityGap).count(),
    )


def test_no_evidence_at_all_is_no_current_evidence(db_session):
    athlete = _athlete(db_session)
    metric = _threshold_pace_setup(db_session, athlete)

    status = compute_status(db_session, athlete.id, metric.id)
    assert status.state == "no_current_evidence"
    assert status.recompute_required is False


def test_pending_snapshot_with_no_assessment_yet_is_recompute_required(db_session):
    """Restored per the approved plan §D8 (independent review, second pass): pending source
    snapshots are evaluated BEFORE assessment selection — this applies even when zero
    `CapabilityAssessment` rows have ever been ingested. A prior correction wrongly reported
    `no_current_evidence` here; the approved contract requires `recompute_required` regardless of
    whether any assessment currently exists, precisely because pending evidence means the answer
    isn't settled yet."""
    athlete = _athlete(db_session)
    metric = _threshold_pace_setup(db_session, athlete)
    db_session.add(BenchmarkResult(athlete_id=athlete.id, benchmark_id=TEN_K_BENCHMARK_ID, completed_at=datetime(2026, 9, 1), raw_value=2400.0, context={}, notes=""))
    db_session.commit()

    before = _all_table_counts(db_session)
    status = compute_status(db_session, athlete.id, metric.id)
    after = _all_table_counts(db_session)

    assert status.state == "recompute_required"
    assert status.recompute_required is True
    assert status.pending_source_snapshot_count == 1
    # No previous chain has ever been computed, so all three stay null.
    assert status.current_assessment is None
    assert status.current_score is None
    assert status.current_gap is None
    assert before == after  # strictly read-only


def test_pending_snapshot_with_a_prior_complete_chain_returns_it_as_stale(db_session):
    """The other half of §D8's contract: when a previous complete chain DOES exist, pending
    evidence still forces `recompute_required`, but the stored (potentially stale) chain is
    returned rather than nulled — with a status reason that says so."""
    from app.services.capability_ingestion import ingest_all_eligible

    athlete = _athlete(db_session)
    metric = _threshold_pace_setup(db_session, athlete)
    db_session.add(BenchmarkResult(athlete_id=athlete.id, benchmark_id=TEN_K_BENCHMARK_ID, completed_at=datetime(2026, 9, 1), raw_value=2400.0, context={}, notes=""))
    db_session.commit()

    ingest_all_eligible(db_session, athlete.id, metric.id)
    score = compute_score_from_current_assessment(db_session, athlete.id, metric.id)
    gap = compute_gap(db_session, athlete.id, metric.id, score)
    assert compute_status(db_session, athlete.id, metric.id).state == "current"

    # New evidence arrives but is not yet recomputed.
    db_session.add(BenchmarkResult(athlete_id=athlete.id, benchmark_id=TEN_K_BENCHMARK_ID, completed_at=datetime(2026, 9, 15), raw_value=2350.0, context={}, notes=""))
    db_session.commit()

    before = _all_table_counts(db_session)
    status = compute_status(db_session, athlete.id, metric.id)
    after = _all_table_counts(db_session)

    assert status.state == "recompute_required"
    assert status.recompute_required is True
    assert status.pending_source_snapshot_count == 1
    assert status.current_gap.id == gap.id
    assert status.current_score.id == score.id
    assert "may now be stale" in status.status_reason
    assert before == after  # strictly read-only


def test_pending_evidence_takes_precedence_over_otherwise_ambiguous_selection(db_session):
    """§D8: pending source snapshots are checked BEFORE selection — even when the already-ingested
    evidence would resolve as ambiguous under `select_current_assessment`, a pending snapshot
    means the answer isn't settled yet, so `state` must be `recompute_required`, never
    `ambiguous_evidence`."""
    from app.models import CapabilityAssessment as _CA
    from app.services.capability_ingestion import ingest_all_eligible

    athlete = _athlete(db_session)
    metric = _threshold_pace_setup(db_session, athlete)
    db_session.add(BenchmarkResult(athlete_id=athlete.id, benchmark_id=TEN_K_BENCHMARK_ID, completed_at=datetime(2026, 9, 1), raw_value=2400.0, context={}, notes=""))
    db_session.commit()
    ingest_all_eligible(db_session, athlete.id, metric.id)

    # A second, tied, unranked-lineage assessment makes the already-ingested evidence ambiguous.
    tied_time = datetime(2026, 9, 1)
    db_session.add(_CA(
        athlete_id=athlete.id, metric_id=metric.id, raw_value=999.0, derivation_method=None,
        assessment_type="self_report", recorded_at=tied_time, ingested_at=tied_time,
        source_revision=None, evidence_class="coach_derived",
    ))
    db_session.commit()

    # Confirm the ambiguity is real before adding pending evidence.
    from app.services.capability_scoring import select_current_assessment
    assert select_current_assessment(db_session, athlete.id, metric.id).status == "ambiguous_evidence"

    # Now add a genuinely pending (not-yet-ingested) source snapshot.
    db_session.add(BenchmarkResult(athlete_id=athlete.id, benchmark_id=TEN_K_BENCHMARK_ID, completed_at=datetime(2026, 9, 20), raw_value=2300.0, context={}, notes=""))
    db_session.commit()

    status = compute_status(db_session, athlete.id, metric.id)
    assert status.state == "recompute_required"
    assert status.pending_source_snapshot_count == 1


def test_assessment_exists_but_incomplete_chain_is_recompute_required(db_session):
    """The review's literal `recompute_required` case: an assessment has already been ingested
    (so it IS the currently selected assessment) but recompute hasn't run scoring/gap yet for it
    — this is the true "assessment exists, chain doesn't" scenario, distinct from the
    no-assessment-at-all case above."""
    from app.services.capability_ingestion import ingest_all_eligible

    athlete = _athlete(db_session)
    metric = _threshold_pace_setup(db_session, athlete)
    db_session.add(BenchmarkResult(athlete_id=athlete.id, benchmark_id=TEN_K_BENCHMARK_ID, completed_at=datetime(2026, 9, 1), raw_value=2400.0, context={}, notes=""))
    db_session.commit()

    ingest_all_eligible(db_session, athlete.id, metric.id)  # assessment now exists; score/gap don't yet

    status = compute_status(db_session, athlete.id, metric.id)
    assert status.state == "recompute_required"
    assert status.current_assessment is not None
    assert status.current_score is None
    assert status.current_gap is None
    assert status.pending_source_snapshot_count == 0


def test_after_recompute_state_is_current(db_session):
    athlete = _athlete(db_session)
    metric = _threshold_pace_setup(db_session, athlete)
    db_session.add(BenchmarkResult(athlete_id=athlete.id, benchmark_id=TEN_K_BENCHMARK_ID, completed_at=datetime(2026, 9, 1), raw_value=2400.0, context={}, notes=""))
    db_session.commit()

    ingest_all_eligible(db_session, athlete.id, metric.id)
    score = compute_score_from_current_assessment(db_session, athlete.id, metric.id)
    compute_gap(db_session, athlete.id, metric.id, score)

    status = compute_status(db_session, athlete.id, metric.id)
    assert status.state == "current"
    assert status.recompute_required is False
    assert status.pending_source_snapshot_count == 0
    assert status.current_score.id == score.id
    assert status.current_as_of is not None


def test_status_call_itself_never_writes_regardless_of_state(db_session):
    athlete = _athlete(db_session)
    metric = _threshold_pace_setup(db_session, athlete)
    db_session.add(BenchmarkResult(athlete_id=athlete.id, benchmark_id=TEN_K_BENCHMARK_ID, completed_at=datetime(2026, 9, 1), raw_value=2400.0, context={}, notes=""))
    db_session.commit()
    ingest_all_eligible(db_session, athlete.id, metric.id)
    score = compute_score_from_current_assessment(db_session, athlete.id, metric.id)
    compute_gap(db_session, athlete.id, metric.id, score)

    before = _all_table_counts(db_session)
    compute_status(db_session, athlete.id, metric.id)
    compute_status(db_session, athlete.id, metric.id)
    compute_status(db_session, athlete.id, metric.id)
    after = _all_table_counts(db_session)
    assert before == after


def test_invalidated_evidence_reports_no_current_evidence_and_preserves_history(db_session):
    """Defensive test for the structurally-unreachable-today "cleared VO2max" case (plan §D2/§D4
    step 0): if the underlying RecoveryReading's vo2_max is (hypothetically) cleared after an
    assessment/score/gap chain was built from it, status must stop calling that chain current —
    without deleting or mutating the historical rows."""
    athlete = _athlete(db_session)
    metric = _vo2max_setup(db_session)
    reading = record_reading(db_session, athlete.id, date(2026, 8, 1), WearableProvider.APPLE_HEALTH, vo2_max=50.0)
    assessment = ingest_vo2max_from_recovery_reading(db_session, reading)
    score = compute_score_from_current_assessment(db_session, athlete.id, metric.id)
    gap = compute_gap(db_session, athlete.id, metric.id, score)

    status_before = compute_status(db_session, athlete.id, metric.id)
    assert status_before.state == "current"

    # Hypothetically invalidate the source evidence (not reachable via the real record_reading
    # API today, per the plan — simulated directly here to prove the read contract holds).
    reading.vo2_max = None
    db_session.commit()

    status_after = compute_status(db_session, athlete.id, metric.id)
    assert status_after.state == "no_current_evidence"
    assert assessment.id in status_after.inactive_source_evidence
    # Point 3: no_current_evidence must null all three current_* fields — never keep pointing at
    # the now-invalidated historical chain.
    assert status_after.current_assessment is None
    assert status_after.current_score is None
    assert status_after.current_gap is None

    # Historical rows are untouched — never deleted, never mutated.
    assert db_session.get(CapabilityAssessment, assessment.id) is not None
    assert db_session.get(CapabilityScore, score.id) is not None
    assert db_session.get(CapabilityGap, gap.id) is not None


def test_ambiguous_evidence_never_labels_a_historical_chain_as_current(db_session):
    """A prior recompute may have established a real chain; a later tie must never let that
    stale chain masquerade as current once evidence becomes ambiguous."""
    from app.models import CapabilityAssessment as _CA

    athlete = _athlete(db_session)
    metric = _threshold_pace_setup(db_session, athlete)
    db_session.add(BenchmarkDefinition(id="benchmark_5k_time_trial", name="5K Time Trial", protocol_description="", unit="sec", evidence_class="coach_derived"))
    db_session.add(BenchmarkDefinitionMetric(benchmark_id="benchmark_5k_time_trial", metric_id=metric.id))
    db_session.commit()
    db_session.add(BenchmarkResult(athlete_id=athlete.id, benchmark_id=TEN_K_BENCHMARK_ID, completed_at=datetime(2026, 9, 1), raw_value=2400.0, context={}, notes=""))
    db_session.commit()

    ingest_all_eligible(db_session, athlete.id, metric.id)
    score = compute_score_from_current_assessment(db_session, athlete.id, metric.id)
    compute_gap(db_session, athlete.id, metric.id, score)
    assert compute_status(db_session, athlete.id, metric.id).state == "current"

    # A second, competing assessment ties on the SAME recorded_at with a different, unranked
    # lineage — self_report vs. the existing benchmark_result chain — forcing ambiguity.
    tied_time = datetime(2026, 9, 1)
    db_session.add(_CA(
        athlete_id=athlete.id, metric_id=metric.id, raw_value=999.0, derivation_method=None,
        assessment_type="self_report", recorded_at=tied_time, ingested_at=tied_time,
        source_revision=None, evidence_class="coach_derived",
    ))
    db_session.commit()

    status = compute_status(db_session, athlete.id, metric.id)
    assert status.state == "ambiguous_evidence"
    assert status.current_assessment is None
    assert status.current_score is None
    assert status.current_gap is None
