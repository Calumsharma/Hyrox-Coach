import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import WorkoutType


def _uuid() -> str:
    return str(uuid.uuid4())


class TrainingBlock(Base):
    """An N-week periodized block working toward a goal event."""

    __tablename__ = "training_blocks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"), index=True)
    start_date: Mapped[date] = mapped_column(Date)
    length_weeks: Mapped[int] = mapped_column(Integer)
    goal_event_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    goal_time_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Ranked list of weak station slugs this block is weighted to address.
    target_weaknesses: Mapped[list] = mapped_column(JSON, default=list)

    # Explicit, coach/athlete-set schedule rather than inferred from length_weeks —
    # deload/taper placement doesn't follow a fixed ratio across block lengths.
    deload_week_numbers: Mapped[list] = mapped_column(JSON, default=list)
    taper_week_numbers: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    athlete: Mapped["Athlete"] = relationship(back_populates="training_blocks")
    weeks: Mapped[list["TrainingWeek"]] = relationship(back_populates="block", cascade="all, delete-orphan", order_by="TrainingWeek.week_number")


class TrainingWeek(Base):
    __tablename__ = "training_weeks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    block_id: Mapped[str] = mapped_column(String, ForeignKey("training_blocks.id"), index=True)
    week_number: Mapped[int] = mapped_column(Integer)
    phase: Mapped[str] = mapped_column(String)  # base | build | peak | taper

    # 1.0 = the block's original plan for this week. Set by the periodization curve at block creation.
    planned_intensity: Mapped[float] = mapped_column(Float, default=1.0)
    # After recovery-driven adjustment is applied; equals planned_intensity until Phase 3 wires the recovery engine in.
    actual_intensity: Mapped[float] = mapped_column(Float, default=1.0)

    block: Mapped["TrainingBlock"] = relationship(back_populates="weeks")
    workouts: Mapped[list["Workout"]] = relationship(back_populates="week", cascade="all, delete-orphan")


class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    week_id: Mapped[str] = mapped_column(String, ForeignKey("training_weeks.id"), index=True)
    day_of_week: Mapped[int] = mapped_column(Integer)  # 0=Mon .. 6=Sun
    workout_type: Mapped[WorkoutType] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)

    # Structured prescription, e.g. {"intervals": "6x1km @ HYROX pace", "target_station": "sled_push"}
    prescription: Mapped[dict] = mapped_column(JSON, default=dict)
    logged_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    week: Mapped["TrainingWeek"] = relationship(back_populates="workouts")
