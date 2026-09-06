import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class NutritionProfile(Base):
    __tablename__ = "nutrition_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"), unique=True)

    sensitivities: Mapped[list] = mapped_column(JSON, default=list)  # e.g. ["lactose", "gluten"]

    daily_calories: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    protein_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    carbs_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fat_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    athlete: Mapped["Athlete"] = relationship(back_populates="nutrition_profile")
    guidance_log: Mapped[list["NutritionGuidance"]] = relationship(back_populates="profile", cascade="all, delete-orphan")


class NutritionGuidance(Base):
    """A single AI-generated nutrition guidance entry (meal suggestions, things to avoid, timing notes)."""

    __tablename__ = "nutrition_guidance"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(String, ForeignKey("nutrition_profiles.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    content: Mapped[str] = mapped_column(String)  # AI-generated guidance text
    context: Mapped[dict] = mapped_column(JSON, default=dict)  # inputs used to generate it, for auditability

    profile: Mapped["NutritionProfile"] = relationship(back_populates="guidance_log")
