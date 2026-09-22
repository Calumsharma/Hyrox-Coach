import uuid
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class SchedulingConstraint(Base):
    """An athlete's real weekly availability. Athlete-editable.

    One row per day the athlete has something to say about; a day with no row is assumed fully
    available with no duration cap — this table only ever narrows the default.
    """

    __tablename__ = "scheduling_constraints"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"), index=True)
    day_of_week: Mapped[int] = mapped_column(Integer)  # 0=Mon .. 6=Sun
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    max_duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(String, default="")
