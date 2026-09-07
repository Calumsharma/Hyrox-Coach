"""Populate StationReference and AccessoryMovement tables. Safe to re-run (upserts by primary key)."""

from app.db import SessionLocal
from app.models import StationReference, AccessoryMovement, ExerciseReference
from app.seed_data.stations import STATIONS
from app.seed_data.accessory_movements import ACCESSORY_MOVEMENTS
from app.seed_data.exercises import EXERCISES


def run():
    db = SessionLocal()
    try:
        for row in STATIONS:
            existing = db.get(StationReference, row["slug"])
            if existing:
                for key, value in row.items():
                    setattr(existing, key, value)
            else:
                db.add(StationReference(**row))

        for row in ACCESSORY_MOVEMENTS:
            existing = db.get(AccessoryMovement, row["id"])
            if existing:
                for key, value in row.items():
                    setattr(existing, key, value)
            else:
                db.add(AccessoryMovement(**row))

        for row in EXERCISES:
            existing = db.get(ExerciseReference, row["slug"])
            if existing:
                for key, value in row.items():
                    setattr(existing, key, value)
            else:
                db.add(ExerciseReference(**row))

        db.commit()
        print(f"Seeded {len(STATIONS)} stations, {len(ACCESSORY_MOVEMENTS)} accessory movements, {len(EXERCISES)} exercises.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
