from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import create_access_token
from app.db import get_db
from app.models import Athlete

router = APIRouter(prefix="/auth", tags=["auth"])


class DevLoginRequest(BaseModel):
    email: str


class TokenResponse(BaseModel):
    access_token: str
    athlete_id: str


@router.post("/dev-login", response_model=TokenResponse)
def dev_login(payload: DevLoginRequest, db: Session = Depends(get_db)):
    """Local-development stand-in for Sign in with Apple.

    Creates an athlete record by email if one doesn't exist yet and returns our JWT.
    Must be replaced with real Apple identity-token verification before shipping.
    """
    athlete = db.query(Athlete).filter(Athlete.email == payload.email).first()
    if athlete is None:
        athlete = Athlete(email=payload.email)
        db.add(athlete)
        db.commit()
        db.refresh(athlete)

    return TokenResponse(access_token=create_access_token(athlete.id), athlete_id=athlete.id)
