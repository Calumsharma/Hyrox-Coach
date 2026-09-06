from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_athlete
from app.db import get_db
from app.models import Athlete, TrainingBlock
from app.schemas.training import TrainingBlockCreate, TrainingBlockRead
from app.services.program_engine import generate_training_block

router = APIRouter(prefix="/training-blocks", tags=["training"])


@router.post("", response_model=TrainingBlockRead)
def create_training_block(
    payload: TrainingBlockCreate,
    athlete: Athlete = Depends(get_current_athlete),
    db: Session = Depends(get_db),
):
    return generate_training_block(
        db=db,
        athlete=athlete,
        length_weeks=payload.length_weeks,
        start_date=payload.start_date,
        goal_event_date=payload.goal_event_date,
        goal_time_seconds=payload.goal_time_seconds,
        deload_week_numbers=payload.deload_week_numbers,
        taper_week_numbers=payload.taper_week_numbers,
    )


@router.get("/current", response_model=Optional[TrainingBlockRead])
def get_current_block(
    athlete: Athlete = Depends(get_current_athlete),
    db: Session = Depends(get_db),
):
    return (
        db.query(TrainingBlock)
        .filter(TrainingBlock.athlete_id == athlete.id)
        .order_by(TrainingBlock.start_date.desc())
        .first()
    )
