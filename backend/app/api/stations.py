from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import StationReference
from app.schemas.station import StationRead

router = APIRouter(prefix="/stations", tags=["stations"])


@router.get("", response_model=list[StationRead])
def list_stations(db: Session = Depends(get_db)):
    return db.query(StationReference).order_by(StationReference.order).all()
