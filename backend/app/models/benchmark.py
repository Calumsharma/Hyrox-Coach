"""Program Engine v5 Milestone 1B — benchmark protocol tables. See app/models/capability.py
for the full milestone context; this module holds the three benchmark-specific tables."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import EvidenceClass
from app.models.immutability import enforce_immutable


def _uuid() -> str:
    return str(uuid.uuid4())


class BenchmarkDefinition(Base):
    """Immutable seed definition. A named test protocol (e.g. "5K time trial", "back squat
    1RM"). No capability_ids JSON list — coverage is expressed via BenchmarkDefinitionMetric,
    a real join table, instead of an unenforced list of ids."""

    __tablename__ = "benchmark_definitions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    protocol_description: Mapped[str] = mapped_column(Text, default="")
    unit: Mapped[str] = mapped_column(String, nullable=False)
    evidence_class: Mapped[EvidenceClass] = mapped_column(String, default=EvidenceClass.COACH_DERIVED)


class BenchmarkDefinitionMetric(Base):
    """Immutable. Plain join table — no athlete dimension, so no composite-FK trick is needed
    here, unlike CapabilityScoreAssessment."""

    __tablename__ = "benchmark_definition_metrics"
    __table_args__ = (UniqueConstraint("benchmark_id", "metric_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    benchmark_id: Mapped[str] = mapped_column(
        String, ForeignKey("benchmark_definitions.id", ondelete="RESTRICT"), nullable=False
    )
    metric_id: Mapped[str] = mapped_column(
        String, ForeignKey("capability_metrics.id", ondelete="RESTRICT"), nullable=False
    )


class BenchmarkResult(Base):
    """Immutable. An athlete's real completed benchmark attempt. UNIQUE(id, athlete_id) is
    the composite-FK target CapabilityAssessment.benchmark_result_id relies on to enforce
    that a cited benchmark result belongs to the same athlete as the assessment citing it."""

    __tablename__ = "benchmark_results"
    __table_args__ = (UniqueConstraint("id", "athlete_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id", ondelete="RESTRICT"), nullable=False)
    benchmark_id: Mapped[str] = mapped_column(
        String, ForeignKey("benchmark_definitions.id", ondelete="RESTRICT"), nullable=False
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    raw_value: Mapped[float] = mapped_column(Float, nullable=False)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str] = mapped_column(Text, default="")


for _model in (BenchmarkDefinition, BenchmarkDefinitionMetric, BenchmarkResult):
    enforce_immutable(_model)
