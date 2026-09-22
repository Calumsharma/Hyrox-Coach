import uuid
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class SchedulingConstraint(Base):
    """An athlete's real weekly availability. Athlete-editable.

    One row per day the athlete has something to say about; a day with no row is assumed fully
    available with no duration cap — this table only ever narrows the default. At most one row
    per (athlete_id, day_of_week) — a second row for the same athlete/day would be ambiguous
    about which one applies. Constraints added in migration 0003_1a_hardening (a Milestone 1A
    hardening pass, not the original 0002_v5_foundations creation).
    """

    __tablename__ = "scheduling_constraints"
    __table_args__ = (
        UniqueConstraint("athlete_id", "day_of_week", name="uq_scheduling_constraint_athlete_day"),
        CheckConstraint("day_of_week BETWEEN 0 AND 6", name="ck_scheduling_constraint_day_of_week_range"),
        CheckConstraint(
            "max_duration_minutes IS NULL OR max_duration_minutes > 0",
            name="ck_scheduling_constraint_max_duration_positive",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"), index=True)
    day_of_week: Mapped[int] = mapped_column(Integer)  # 0=Mon .. 6=Sun
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    max_duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(String, default="")
