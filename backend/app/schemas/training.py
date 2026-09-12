from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import Discipline, WorkoutType


class TrainingBlockCreate(BaseModel):
    length_weeks: int
    start_date: date
    goal_event_date: date
    goal_time_seconds: int
    discipline: Discipline = Discipline.HYROX
    # Explicit, coach/athlete-set schedule. Omit to use the server's suggested default
    # (every 4th week deloads, the final week tapers) rather than a fixed ratio.
    deload_week_numbers: list[int] | None = None
    taper_week_numbers: list[int] | None = None


class SetLog(BaseModel):
    reps: int | None = None
    weight_kg: float | None = None


class BlockLog(BaseModel):
    """One logged block, matched back to `prescription["blocks"][index]` by position."""

    index: int
    sets: list[SetLog] = []
    actual_time_sec: int | None = None
    actual_distance_m: float | None = None
    rpe: float | None = None  # 1-10, Borg CR10-style perceived exertion


class ConditioningLog(BaseModel):
    """For AMRAP/rounds-format conditioning, where the meaningful outcome isn't sets/reps
    but how far the athlete got and how hard it was."""

    rounds_completed: int | None = None
    extra_reps: int | None = None
    duration_sec: int | None = None
    rpe: float | None = None


class WorkoutLogUpdate(BaseModel):
    notes: str | None = None
    blocks: list[BlockLog] = []
    conditioning: ConditioningLog | None = None


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
    discipline: Discipline
    start_date: date
    length_weeks: int
    goal_event_date: date | None
    goal_time_seconds: int | None
    target_weaknesses: list[str]
    deload_week_numbers: list[int]
    taper_week_numbers: list[int]
    weeks: list[TrainingWeekRead]
