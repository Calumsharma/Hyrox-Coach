from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.enums import Division, ExperienceTier, StationSlug


class PastResultCreate(BaseModel):
    event_date: date
    division: Division
    total_time_seconds: int
    station_splits_seconds: dict[str, int] = {}


class PastResultRead(PastResultCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str


class AthleteOnboarding(BaseModel):
    """Filled in during the onboarding flow, after sign-in has created a bare athlete record."""

    name: str
    age: int
    weight_kg: float
    height_cm: float
    division: Division
    experience_tier: ExperienceTier
    tested_max_hr: int | None = None
    predicted_5k_seconds: int | None = None
    current_10k_seconds: int | None = None
    self_reported_weak_stations: list[StationSlug] = []
    goal_time_seconds: int | None = None
    goal_event_date: date | None = None


class AthleteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    name: str | None
    age: int | None
    weight_kg: float | None
    height_cm: float | None
    division: Division | None
    experience_tier: ExperienceTier | None
    tested_max_hr: int | None
    onboarding_completed: bool
    predicted_5k_seconds: int | None
    current_10k_seconds: int | None
    self_reported_weak_stations: list[StationSlug]
    goal_time_seconds: int | None
    goal_event_date: date | None
    past_results: list[PastResultRead] = []
