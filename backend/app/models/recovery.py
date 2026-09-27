import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import RecoveryTrend, WearableProvider


def _uuid() -> str:
    return str(uuid.uuid4())


class WearableConnection(Base):
    __tablename__ = "wearable_connections"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"))
    provider: Mapped[WearableProvider] = mapped_column(String)
    access_token: Mapped[str] = mapped_column(String)
    refresh_token: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    athlete: Mapped["Athlete"] = relationship(back_populates="wearable_connections")


class RecoveryReading(Base):
    """One day's raw recovery inputs, normalized from whichever wearable provider supplied them."""

    __tablename__ = "recovery_readings"
    __table_args__ = (
        # Composite target for CapabilityAssessment.recovery_reading_id's composite FK
        # (Program Engine v5 Milestone 1B) — enforces a cited reading belongs to the same
        # athlete as the assessment citing it, at the database level.
        UniqueConstraint("id", "athlete_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"), index=True)
    reading_date: Mapped[date] = mapped_column(Date, index=True)
    source: Mapped[WearableProvider] = mapped_column(String)

    hrv_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    resting_hr_bpm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sleep_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100
    vo2_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Program Engine v5 Milestone 2 (migration 0005) — field-level VO2max provenance, distinct
    # from the bare `source` column above. `source` reflects whichever provider most recently
    # synced ANY field on this row, which is NOT necessarily the provider that supplied the
    # currently-stored `vo2_max` value if a later sync from a different provider only touched
    # HRV/sleep. These three fields are set only by `record_reading` when `vo2_max` itself
    # actually changes (see app/services/recovery_engine.py) — NULL on every row that predates
    # this migration, never guessed. `vo2_max_updated_at` doubles as the source-revision marker
    # capability ingestion uses to distinguish a genuine re-measurement from an unchanged resync.
    vo2_max_source: Mapped[Optional[WearableProvider]] = mapped_column(String, nullable=True)
    vo2_max_recorded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    vo2_max_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RecoveryScore(Base):
    """Daily composite recovery score, z-scored against the athlete's own rolling baseline. Drives program adjustment."""

    __tablename__ = "recovery_scores"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"), index=True)
    score_date: Mapped[date] = mapped_column(Date, index=True)

    composite_score: Mapped[float] = mapped_column(Float)  # 0-100
    trend: Mapped[RecoveryTrend] = mapped_column(String)
    hrv_z: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    resting_hr_z: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sleep_z: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
