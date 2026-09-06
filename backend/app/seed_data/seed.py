"""Populate StationReference and AccessoryMovement tables. Safe to re-run (upserts by primary key)."""

from app.db import SessionLocal
from app.models import StationReference, AccessoryMovement
from app.seed_data.stations import STATIONS
from app.seed_data.accessory_movements import ACCESSORY_MOVEMENTS


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

        db.commit()
        print(f"Seeded {len(STATIONS)} stations and {len(ACCESSORY_MOVEMENTS)} accessory movements.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
