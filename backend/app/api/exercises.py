from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ExerciseReference
from app.schemas.exercise import ExerciseRead

router = APIRouter(prefix="/exercises", tags=["exercises"])


@router.get("", response_model=list[ExerciseRead])
def list_exercises(db: Session = Depends(get_db)):
    return db.query(ExerciseReference).order_by(ExerciseReference.name).all()


@router.get("/{slug}", response_model=ExerciseRead)
def get_exercise(slug: str, db: Session = Depends(get_db)):
    exercise = db.get(ExerciseReference, slug)
    if exercise is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    return exercise
