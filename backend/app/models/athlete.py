import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import Division, ExperienceTier


def _uuid() -> str:
    return str(uuid.uuid4())


class Athlete(Base):
    __tablename__ = "athletes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    division: Mapped[Optional[Division]] = mapped_column(String, nullable=True)
    experience_tier: Mapped[Optional[ExperienceTier]] = mapped_column(String, nullable=True)
    onboarding_completed: Mapped[bool] = mapped_column(default=False)

    predicted_5k_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_10k_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Free-form list of station slugs the athlete self-reports as weak, ordered worst-first.
    self_reported_weak_stations: Mapped[list] = mapped_column(JSON, default=list)

    goal_time_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    goal_event_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    past_results: Mapped[list["PastHyroxResult"]] = relationship(back_populates="athlete", cascade="all, delete-orphan")
    wearable_connections: Mapped[list["WearableConnection"]] = relationship(back_populates="athlete", cascade="all, delete-orphan")
    training_blocks: Mapped[list["TrainingBlock"]] = relationship(back_populates="athlete", cascade="all, delete-orphan")
    nutrition_profile: Mapped["NutritionProfile"] = relationship(back_populates="athlete", uselist=False, cascade="all, delete-orphan")


class PastHyroxResult(Base):
    """A previous HYROX race result, optionally with per-station splits used to rank weaknesses objectively."""

    __tablename__ = "past_hyrox_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"))
    event_date: Mapped[date] = mapped_column(Date)
    division: Mapped[Division] = mapped_column(String)
    total_time_seconds: Mapped[int] = mapped_column(Integer)

    # {"skierg": 312, "sled_push": 210, ...} run splits keyed "run_1".."run_8", station splits keyed by StationSlug.
    station_splits_seconds: Mapped[dict] = mapped_column(JSON, default=dict)

    athlete: Mapped["Athlete"] = relationship(back_populates="past_results")
