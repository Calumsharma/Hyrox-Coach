from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_athlete
from app.db import get_db
from app.models import Athlete, TrainingBlock, TrainingWeek, Workout
from app.schemas.training import WorkoutLogUpdate, WorkoutRead
from app.services.progression_engine import apply_progression

router = APIRouter(prefix="/workouts", tags=["workouts"])


def _get_owned_workout(workout_id: str, athlete: Athlete, db: Session) -> Workout:
    workout = (
        db.query(Workout)
        .join(TrainingWeek)
        .join(TrainingBlock)
        .filter(Workout.id == workout_id, TrainingBlock.athlete_id == athlete.id)
        .options(joinedload(Workout.week))
        .first()
    )
    if workout is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")
    return workout


@router.patch("/{workout_id}/log", response_model=WorkoutRead)
def log_workout(
    workout_id: str,
    payload: WorkoutLogUpdate,
    athlete: Athlete = Depends(get_current_athlete),
    db: Session = Depends(get_db),
):
    workout = _get_owned_workout(workout_id, athlete, db)
    workout.logged_result = payload.model_dump(exclude_none=True)
    workout.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(workout)

    apply_progression(db, workout, payload)

    return workout
