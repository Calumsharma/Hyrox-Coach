from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_athlete
from app.db import get_db
from app.models import Athlete, PastHyroxResult
from app.models.enums import ExperienceTier
from app.schemas.athlete import AthleteOnboarding, AthleteRead, PastResultCreate, PastResultRead
from app.services.experience_tier import suggest_tier_from_inputs

router = APIRouter(prefix="/athletes", tags=["athletes"])


class TierSuggestionRequest(BaseModel):
    best_solo_time_seconds: int | None = None
    race_count: int = 0


class TierSuggestionResponse(BaseModel):
    suggested_tier: ExperienceTier


@router.post("/tier-suggestion", response_model=TierSuggestionResponse)
def suggest_tier(payload: TierSuggestionRequest):
    return TierSuggestionResponse(
        suggested_tier=suggest_tier_from_inputs(payload.best_solo_time_seconds, payload.race_count)
    )


@router.get("/me", response_model=AthleteRead)
def get_me(athlete: Athlete = Depends(get_current_athlete)):
    return athlete


@router.put("/me/onboarding", response_model=AthleteRead)
def complete_onboarding(
    payload: AthleteOnboarding,
    athlete: Athlete = Depends(get_current_athlete),
    db: Session = Depends(get_db),
):
    for key, value in payload.model_dump().items():
        setattr(athlete, key, value)
    athlete.onboarding_completed = True
    db.commit()
    db.refresh(athlete)
    return athlete


@router.post("/me/past-results", response_model=PastResultRead)
def add_past_result(
    payload: PastResultCreate,
    athlete: Athlete = Depends(get_current_athlete),
    db: Session = Depends(get_db),
):
    result = PastHyroxResult(athlete_id=athlete.id, **payload.model_dump())
    db.add(result)
    db.commit()
    db.refresh(result)
    return result
