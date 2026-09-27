"""VO2max and threshold-pace ingestion — Program Engine v5 Milestone 2, plan §D2/§D3. Also
exercises the corrected `record_reading` VO2max field-provenance fix directly, since ingestion
depends on it for `source_revision`/timestamp correctness."""

from datetime import date, datetime

import pytest

from app.models import (
    Athlete,
    BenchmarkDefinition,
    BenchmarkDefinitionMetric,
    BenchmarkResult,
    CapabilityDefinition,
    CapabilityMetric,
)
from app.models.enums import WearableProvider
from app.seed_data.benchmarks import (
    BENCHMARK_DEFINITION_METRICS,
    BENCHMARK_DEFINITIONS,
    FIVE_K_BENCHMARK_ID,
    TEN_K_BENCHMARK_ID,
)
from app.seed_data.capabilities import CAPABILITY_DEFINITIONS
from app.seed_data.capability_metrics import CAPABILITY_METRICS
from app.services.capability_ingestion import (
    UnsupportedBenchmarkError,
    ingest_threshold_pace_from_benchmark_result,
    ingest_vo2max_from_recovery_reading,
)
from app.services.recovery_engine import record_reading


def _seed_capability_schema(db_session):
    for row in CAPABILITY_DEFINITIONS:
        db_session.add(CapabilityDefinition(**row))
    db_session.commit()
    for row in CAPABILITY_METRICS:
        db_session.add(CapabilityMetric(**row))
    db_session.commit()
    for row in BENCHMARK_DEFINITIONS:
        db_session.add(BenchmarkDefinition(**row))
    db_session.commit()
    for row in BENCHMARK_DEFINITION_METRICS:
        db_session.add(BenchmarkDefinitionMetric(**row))
    db_session.commit()


def _athlete(db_session, email="cap-ingest@example.com"):
    athlete = Athlete(email=email)
    db_session.add(athlete)
    db_session.commit()
    return athlete


@pytest.fixture
def seeded(db_session):
    _seed_capability_schema(db_session)
    return db_session


def test_vo2max_ingestion_sets_recorded_at_from_reading_date_not_created_at(seeded):
    athlete = _athlete(seeded)
    reading = record_reading(seeded, athlete.id, date(2026, 8, 1), WearableProvider.APPLE_HEALTH, vo2_max=50.0)

    assessment = ingest_vo2max_from_recovery_reading(seeded, reading)

    assert assessment is not None
    assert assessment.raw_value == 50.0
    assert assessment.derivation_method is None
    assert assessment.assessment_type == "wearable_derived"
    assert assessment.recorded_at == datetime(2026, 8, 1, 0, 0, 0)
    assert assessment.source_revision is not None
    assert "source_provider=apple_health" in assessment.context_note


def test_vo2max_ingestion_returns_none_when_no_value(seeded):
    athlete = _athlete(seeded)
    reading = record_reading(seeded, athlete.id, date(2026, 8, 1), WearableProvider.APPLE_HEALTH, hrv_ms=55.0)
    assert ingest_vo2max_from_recovery_reading(seeded, reading) is None


def test_vo2max_changed_value_produces_new_assessment_not_duplicate(seeded):
    athlete = _athlete(seeded)
    reading = record_reading(seeded, athlete.id, date(2026, 8, 1), WearableProvider.APPLE_HEALTH, vo2_max=50.0)
    a1 = ingest_vo2max_from_recovery_reading(seeded, reading)

    reading = record_reading(seeded, athlete.id, date(2026, 8, 1), WearableProvider.GARMIN, vo2_max=51.0)
    a2 = ingest_vo2max_from_recovery_reading(seeded, reading)

    assert a1.id != a2.id
    assert a2.raw_value == 51.0
    assert a2.source_revision != a1.source_revision


def test_vo2max_50_51_50_produces_three_distinct_correctly_ordered_assessments(seeded):
    """The exact case your review named: a value that repeats must not be mistaken for the
    original — each genuine revision gets its own assessment."""
    athlete = _athlete(seeded)

    reading = record_reading(seeded, athlete.id, date(2026, 8, 1), WearableProvider.APPLE_HEALTH, vo2_max=50.0)
    a1 = ingest_vo2max_from_recovery_reading(seeded, reading)

    reading = record_reading(seeded, athlete.id, date(2026, 8, 1), WearableProvider.APPLE_HEALTH, vo2_max=51.0)
    a2 = ingest_vo2max_from_recovery_reading(seeded, reading)

    reading = record_reading(seeded, athlete.id, date(2026, 8, 1), WearableProvider.APPLE_HEALTH, vo2_max=50.0)
    a3 = ingest_vo2max_from_recovery_reading(seeded, reading)

    assert len({a1.id, a2.id, a3.id}) == 3
    assert a1.raw_value == a3.raw_value == 50.0
    assert a2.raw_value == 51.0
    assert a3.source_revision not in (a1.source_revision, a2.source_revision)


def test_vo2max_unchanged_resync_is_a_true_noop(seeded):
    athlete = _athlete(seeded)
    reading = record_reading(seeded, athlete.id, date(2026, 8, 1), WearableProvider.APPLE_HEALTH, vo2_max=50.0)
    a1 = ingest_vo2max_from_recovery_reading(seeded, reading)

    reading = record_reading(seeded, athlete.id, date(2026, 8, 1), WearableProvider.APPLE_HEALTH, vo2_max=50.0)
    a2 = ingest_vo2max_from_recovery_reading(seeded, reading)

    assert a1.id == a2.id


def test_legacy_reading_without_updated_at_uses_unknown_historical_sentinel(seeded):
    """Simulates a RecoveryReading that predates migration 0005: a real vo2_max value, but the
    provenance fields were never populated. Ingestion must never guess a real revision here."""
    athlete = _athlete(seeded)
    reading = record_reading(seeded, athlete.id, date(2026, 8, 1), WearableProvider.APPLE_HEALTH, hrv_ms=55.0)
    reading.vo2_max = 50.0  # bypasses record_reading's provenance-setting logic on purpose
    seeded.commit()
    seeded.refresh(reading)

    assessment = ingest_vo2max_from_recovery_reading(seeded, reading)
    assert assessment.source_revision == "unknown_historical"
    assert "source_provider=unknown" in assessment.context_note


def test_threshold_pace_from_10k_is_pure_unit_conversion(seeded):
    athlete = _athlete(seeded)
    result = BenchmarkResult(
        athlete_id=athlete.id, benchmark_id=TEN_K_BENCHMARK_ID, completed_at=datetime(2026, 8, 1),
        raw_value=2400.0, context={}, notes="",
    )
    seeded.add(result)
    seeded.commit()

    assessment = ingest_threshold_pace_from_benchmark_result(seeded, result)
    assert assessment.derivation_method == "pace_from_10k_time_trial_v1"
    assert assessment.raw_value == pytest.approx(240.0)


def test_threshold_pace_from_5k_uses_riegel(seeded):
    athlete = _athlete(seeded)
    result = BenchmarkResult(
        athlete_id=athlete.id, benchmark_id=FIVE_K_BENCHMARK_ID, completed_at=datetime(2026, 8, 1),
        raw_value=1200.0, context={}, notes="",
    )
    seeded.add(result)
    seeded.commit()

    assessment = ingest_threshold_pace_from_benchmark_result(seeded, result)
    assert assessment.derivation_method == "riegel_threshold_pace_from_5k_v1"
    expected = 1200.0 * (2.0 ** 1.06) / 10.0
    assert assessment.raw_value == pytest.approx(expected, rel=1e-9)


def test_unsupported_benchmark_id_raises():
    class _FakeBenchmarkResult:
        benchmark_id = "not_a_real_benchmark"

    with pytest.raises(UnsupportedBenchmarkError):
        ingest_threshold_pace_from_benchmark_result(None, _FakeBenchmarkResult())
