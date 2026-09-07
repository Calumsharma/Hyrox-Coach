from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.enums import RecoveryTrend, WearableProvider
from app.schemas.training import TrainingWeekRead


class RecoveryReadingCreate(BaseModel):
    reading_date: date
    source: WearableProvider = WearableProvider.APPLE_HEALTH
    hrv_ms: float | None = None
    resting_hr_bpm: float | None = None
    sleep_score: float | None = None
    vo2_max: float | None = None


class RecoveryScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    score_date: date
    composite_score: float
    trend: RecoveryTrend
    hrv_z: float | None
    resting_hr_z: float | None
    sleep_z: float | None


class RecoveryUpdateResponse(BaseModel):
    score: RecoveryScoreRead
    adjusted_week: TrainingWeekRead | None
