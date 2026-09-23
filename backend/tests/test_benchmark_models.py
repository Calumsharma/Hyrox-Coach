"""CRUD round-trip for BenchmarkDefinition/BenchmarkDefinitionMetric/BenchmarkResult —
Program Engine v5 Milestone 1B."""

from datetime import datetime

from app.models import (
    Athlete,
    BenchmarkDefinition,
    BenchmarkDefinitionMetric,
    BenchmarkResult,
    CapabilityDefinition,
    CapabilityMetric,
)


def _metric(db_session):
    definition = CapabilityDefinition(id="max_relative_strength", name="Max Relative Strength", description="", measurement_hint="")
    metric = CapabilityMetric(
        id="relative_strength_squat_1rm_per_bodyweight",
        capability_id="max_relative_strength",
        station=None,
        unit="ratio",
        higher_is_better=True,
        evidence_class="coach_derived",
        description="",
    )
    db_session.add_all([definition, metric])
    db_session.commit()
    return metric


def test_benchmark_definition_create_and_read(db_session):
    definition = BenchmarkDefinition(name="Back Squat 1RM", protocol_description="Standard 1RM test.", unit="kg", evidence_class="coach_derived")
    db_session.add(definition)
    db_session.commit()

    fetched = db_session.get(BenchmarkDefinition, definition.id)
    assert fetched.name == "Back Squat 1RM"
    assert fetched.unit == "kg"


def test_benchmark_definition_metric_create_and_read(db_session):
    metric = _metric(db_session)
    definition = BenchmarkDefinition(name="Back Squat 1RM", protocol_description="", unit="kg", evidence_class="coach_derived")
    db_session.add(definition)
    db_session.commit()

    link = BenchmarkDefinitionMetric(benchmark_id=definition.id, metric_id=metric.id)
    db_session.add(link)
    db_session.commit()

    fetched = db_session.get(BenchmarkDefinitionMetric, link.id)
    assert fetched.benchmark_id == definition.id
    assert fetched.metric_id == metric.id


def test_benchmark_result_create_and_read(db_session):
    athlete = Athlete(email="benchmark@example.com")
    db_session.add(athlete)
    db_session.commit()

    definition = BenchmarkDefinition(name="Back Squat 1RM", protocol_description="", unit="kg", evidence_class="coach_derived")
    db_session.add(definition)
    db_session.commit()

    result = BenchmarkResult(
        athlete_id=athlete.id,
        benchmark_id=definition.id,
        completed_at=datetime(2026, 9, 1),
        raw_value=120.0,
        context={"bodyweight_kg": 82.5},
        notes="Field test, belt only.",
    )
    db_session.add(result)
    db_session.commit()

    fetched = db_session.get(BenchmarkResult, result.id)
    assert fetched.raw_value == 120.0
    assert fetched.context == {"bodyweight_kg": 82.5}
