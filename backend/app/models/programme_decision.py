import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, JSON, event
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import EvidenceClass, ProgrammeDecisionType


def _uuid() -> str:
    return str(uuid.uuid4())


class ProgrammeDecisionImmutableError(RuntimeError):
    """Raised when application code attempts to update or delete an existing ProgrammeDecision
    row through the ORM. ProgrammeDecision is an append-only audit log — see its docstring.

    Honest scope note: this enforces append-only behaviour on the application's own SQLAlchemy
    ORM path only (via the `before_update`/`before_delete` mapper events registered below). A
    database administrator running raw SQL directly against the database (or any client that
    bypasses this ORM entirely) is NOT stopped by this — that would require database-level
    protection (e.g. SQLite triggers, or Postgres row-level rules/triggers in production),
    which is not part of this milestone and is a real, separate gap if that threat matters.
    """


class ProgrammeDecision(Base):
    """Append-only audit log of every automated or manual change to an athlete's programme.

    Never edited or deleted — enforced at the ORM level via the `before_update`/`before_delete`
    event listeners below, which raise `ProgrammeDecisionImmutableError` (see that class's
    docstring for the exact scope of this protection). `before_state`/`after_state` are explicit
    JSON snapshots, not just a text summary, so cumulative drift across repeated adjustments is
    checkable — see the Program Engine v5 plan's overlay-composition design (§2/§5).
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


@event.listens_for(ProgrammeDecision, "before_update")
def _reject_programme_decision_update(mapper, connection, target):
    raise ProgrammeDecisionImmutableError(
        f"ProgrammeDecision {target.id!r} cannot be updated — rows are append-only once created."
    )


@event.listens_for(ProgrammeDecision, "before_delete")
def _reject_programme_decision_delete(mapper, connection, target):
    raise ProgrammeDecisionImmutableError(
        f"ProgrammeDecision {target.id!r} cannot be deleted — rows are append-only."
    )
