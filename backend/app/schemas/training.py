from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import WorkoutType


class TrainingBlockCreate(BaseModel):
    length_weeks: int
    start_date: date
    goal_event_date: date
    goal_time_seconds: int
    # Explicit, coach/athlete-set schedule. Omit to use the server's suggested default
    # (every 4th week deloads, the final week tapers) rather than a fixed ratio.
    deload_week_numbers: list[int] | None = None
    taper_week_numbers: list[int] | None = None


class WorkoutRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    day_of_week: int
    workout_type: WorkoutType
    title: str
    prescription: dict
    logged_result: dict | None
    completed_at: datetime | None = None


class TrainingWeekRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    week_number: int
    phase: str
    planned_intensity: float
    actual_intensity: float
    workouts: list[WorkoutRead]


class TrainingBlockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    start_date: date
    length_weeks: int
    goal_event_date: date | None
    goal_time_seconds: int | None
    target_weaknesses: list[str]
    deload_week_numbers: list[int]
    taper_week_numbers: list[int]
    weeks: list[TrainingWeekRead]
