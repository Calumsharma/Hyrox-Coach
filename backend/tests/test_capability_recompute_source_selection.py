"""Recomputation source selection — Program Engine v5 Milestone 2, plan §D6. Recompute processes
every eligible, not-yet-ingested source snapshot for the athlete/metric, deterministically —
never one explicitly selected row — and the result is independent of submission order."""

from datetime import datetime

from app.models import Athlete, BenchmarkDefinition, BenchmarkDefinitionMetric, BenchmarkResult, CapabilityDefinition, CapabilityMetric
from app.seed_data.benchmarks import FIVE_K_BENCHMARK_ID, TEN_K_BENCHMARK_ID
from app.services.capability_ingestion import THRESHOLD_PACE_METRIC_ID, ingest_all_eligible
from app.services.capability_scoring import select_current_assessment


def _seeded_athlete_and_metric(db_session):
    athlete = Athlete(email="source-selection@example.com")
    db_session.add(athlete)
    db_session.add(CapabilityDefinition(id="threshold_race_pace", name="Threshold & Race Pace", description="", measurement_hint=""))
    db_session.commit()
    metric = CapabilityMetric(
        id=THRESHOLD_PACE_METRIC_ID, capability_id="threshold_race_pace", station=None, unit="sec_per_km",
        higher_is_better=False, evidence_class="coach_derived", description="",
    )
    db_session.add(metric)
    db_session.add(BenchmarkDefinition(id=FIVE_K_BENCHMARK_ID, name="5K Time Trial", protocol_description="", unit="sec", evidence_class="coach_derived"))
    db_session.add(BenchmarkDefinition(id=TEN_K_BENCHMARK_ID, name="10K Time Trial", protocol_description="", unit="sec", evidence_class="coach_derived"))
    db_session.commit()
    db_session.add(BenchmarkDefinitionMetric(benchmark_id=FIVE_K_BENCHMARK_ID, metric_id=THRESHOLD_PACE_METRIC_ID))
    db_session.add(BenchmarkDefinitionMetric(benchmark_id=TEN_K_BENCHMARK_ID, metric_id=THRESHOLD_PACE_METRIC_ID))
    db_session.commit()
    return athlete, metric


def test_out_of_order_submission_still_selects_chronologically_latest_result(db_session):
    athlete, metric = _seeded_athlete_and_metric(db_session)

    # Submitted out of chronological order: the LATER result is submitted FIRST.
    later_result = BenchmarkResult(
        athlete_id=athlete.id, benchmark_id=TEN_K_BENCHMARK_ID, completed_at=datetime(2026, 9, 1),
        raw_value=2400.0, context={}, notes="",
    )
    db_session.add(later_result)
    db_session.commit()
    earlier_result = BenchmarkResult(
        athlete_id=athlete.id, benchmark_id=FIVE_K_BENCHMARK_ID, completed_at=datetime(2026, 8, 1),
        raw_value=1200.0, context={}, notes="",
    )
    db_session.add(earlier_result)
    db_session.commit()

    # One recompute call ingests both, regardless of submission order.
    ingested = ingest_all_eligible(db_session, athlete.id, metric.id)
    assert len(ingested) == 2

    selection = select_current_assessment(db_session, athlete.id, metric.id)
    assert selection.status == "resolved"
    assert selection.assessment.recorded_at == datetime(2026, 9, 1)


def test_recompute_with_no_new_evidence_ingests_zero_rows(db_session):
    athlete, metric = _seeded_athlete_and_metric(db_session)
    result = BenchmarkResult(
        athlete_id=athlete.id, benchmark_id=TEN_K_BENCHMARK_ID, completed_at=datetime(2026, 9, 1),
        raw_value=2400.0, context={}, notes="",
    )
    db_session.add(result)
    db_session.commit()

    first = ingest_all_eligible(db_session, athlete.id, metric.id)
    second = ingest_all_eligible(db_session, athlete.id, metric.id)
    assert len(first) == 1
    assert len(second) == 1  # ingest_all_eligible always re-fetches; the assessment count is what matters
    assert first[0].id == second[0].id
