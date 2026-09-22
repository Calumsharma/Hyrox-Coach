import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import EvidenceClass, ProgrammeDecisionType


def _uuid() -> str:
    return str(uuid.uuid4())


class ProgrammeDecision(Base):
    """Append-only audit log of every automated or manual change to an athlete's programme.

    Never edited or deleted. `before_state`/`after_state` are explicit JSON snapshots, not just
    a text summary, so cumulative drift across repeated adjustments is checkable — see the
    Program Engine v5 plan's overlay-composition design (§2/§5).
    """

    __tablename__ = "programme_decisions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"), index=True)
    training_week_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("training_weeks.id"), nullable=True)
    athlete_session_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("workouts.id"), nullable=True)

    decision_type: Mapped[ProgrammeDecisionType] = mapped_column(String)
    summary: Mapped[str] = mapped_column(String, default="")

    before_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    after_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    schema_version: Mapped[str] = mapped_column(String, default="1")
    # Which RaceRuleSet/ConstraintPolicy/CapabilityBandPolicy versions were active when this
    # decision was made. Only RaceRuleSet exists as of Milestone 1A; nullable so this column is
    # usable before ConstraintPolicy/CapabilityBandPolicy (later milestones) exist.
    rule_set_version: Mapped[Optional[str]] = mapped_column(String, ForeignKey("race_rule_sets.id"), nullable=True)

    evidence_class: Mapped[EvidenceClass] = mapped_column(String, default=EvidenceClass.COACH_DERIVED)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
