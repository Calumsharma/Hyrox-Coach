from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_athlete
from app.db import get_db
from app.models import Athlete, RecoveryScore
from app.schemas.recovery import RecoveryReadingCreate, RecoveryScoreRead, RecoveryUpdateResponse
from app.services.recovery_engine import apply_recovery_adjustment, compute_and_store_score, record_reading

router = APIRouter(prefix="/recovery", tags=["recovery"])


@router.post("/readings", response_model=RecoveryUpdateResponse)
def submit_reading(
    payload: RecoveryReadingCreate,
    athlete: Athlete = Depends(get_current_athlete),
    db: Session = Depends(get_db),
):
    """Records a day's recovery reading (manual entry today; a Terra/wearable webhook would
    call `record_reading` the same way once that's wired up) and immediately re-scores and
    applies any resulting adjustment to the athlete's current training week."""

    record_reading(
        db=db,
        athlete_id=athlete.id,
        reading_date=payload.reading_date,
        source=payload.source,
        hrv_ms=payload.hrv_ms,
        resting_hr_bpm=payload.resting_hr_bpm,
        sleep_score=payload.sleep_score,
        vo2_max=payload.vo2_max,
    )
    score = compute_and_store_score(db, athlete.id, payload.reading_date)
    adjusted_week = apply_recovery_adjustment(db, athlete.id, payload.reading_date)
    return RecoveryUpdateResponse(score=score, adjusted_week=adjusted_week)


@router.get("/status", response_model=Optional[RecoveryScoreRead])
def get_recovery_status(
    athlete: Athlete = Depends(get_current_athlete),
    db: Session = Depends(get_db),
):
    return (
        db.query(RecoveryScore)
        .filter(RecoveryScore.athlete_id == athlete.id)
        .order_by(RecoveryScore.score_date.desc())
        .first()
    )
