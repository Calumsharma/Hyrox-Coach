"""Program Engine v5 Milestone 1B — athlete-reported symptom/pain capture.

Deliberately isolated from the capability-scoring layer: no foreign key from this table into
CapabilityAssessment/Score/Gap anywhere, and nothing in this codebase reads it yet. Pain and
illness are safety signals, not performance evidence, and must never quietly become graded
"evidence" the way CapabilityAssessment rows are. See app/models/capability.py for the wider
Milestone 1B context.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import EffectOnTraining, StatusReportSource, SymptomSeverity
from app.models.immutability import enforce_immutable


def _uuid() -> str:
    return str(uuid.uuid4())


class AthleteStatusReport(Base):
    """Immutable, timestamped, athlete-provided-only. Must not diagnose injury and must not
    infer resilience from silence, missed sessions, or wearable data — enforced structurally
    by the simple fact that nothing in this milestone reads this table at all."""

    __tablename__ = "athlete_status_reports"
    __table_args__ = (
        # StatusReportSource being a Python enum does not restrict what the database will
        # accept — `source` is stored as a plain String column, so an independent audit
        # correctly found a direct insert with an arbitrary string succeeded. This CHECK is
        # the actual database-level enforcement; the Python enum alone was never sufficient.
        CheckConstraint("source = 'athlete_self_report'", name="ck_athlete_status_report_source"),
        CheckConstraint("pain_present = TRUE OR symptom_severity IS NULL OR symptom_severity = 'none'"),
        CheckConstraint(
            "effect_on_training NOT IN ('reduced', 'avoid') OR pain_present = TRUE OR illness_present = TRUE"
        ),
        CheckConstraint(
            "pain_present = TRUE OR illness_present = TRUE OR effect_on_training IS NULL OR effect_on_training = 'none'"
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id", ondelete="RESTRICT"), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    source: Mapped[StatusReportSource] = mapped_column(String, nullable=False, default=StatusReportSource.ATHLETE_SELF_REPORT)
    pain_present: Mapped[bool] = mapped_column(Boolean, nullable=False)
    symptom_severity: Mapped[Optional[SymptomSeverity]] = mapped_column(String, nullable=True)
    body_area: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    illness_present: Mapped[bool] = mapped_column(Boolean, nullable=False)
    effect_on_training: Mapped[Optional[EffectOnTraining]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


enforce_immutable(AthleteStatusReport)
