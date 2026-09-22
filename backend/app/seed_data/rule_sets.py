"""The one official RaceRuleSet row plus a safe backfill onto every StationReference row.

Deliberately holds only version/source metadata (see app/models/rule_set.py's docstring) —
the actual station definitions stay in StationReference/seed_data/stations.py, never
duplicated here. Idempotent and safe to re-run, matching the rest of app/seed_data/seed.py.
"""

from datetime import date

from app.db import SessionLocal
from app.models import RaceRuleSet, StationReference

RACE_RULE_SETS = [
    {
        "id": "hyrox_singles_2026_27",
        "effective_from": date(2026, 1, 1),
        "source_url": "https://hyrox.com/rulebook/",
        "notes": "2026/27 season singles rulebook + division weight charts.",
    },
]


def run():
    db = SessionLocal()
    try:
        for row in RACE_RULE_SETS:
            existing = db.get(RaceRuleSet, row["id"])
            if existing:
                for key, value in row.items():
                    setattr(existing, key, value)
            else:
                db.add(RaceRuleSet(**row))
        db.flush()

        current_rule_set_id = RACE_RULE_SETS[0]["id"]
        unversioned = db.query(StationReference).filter(StationReference.rule_set_version.is_(None)).all()
        for station in unversioned:
            station.rule_set_version = current_rule_set_id
        # SessionLocal is configured with autoflush=False (app/db.py) — an explicit flush is
        # required here, or the verification query below would read stale (pre-update) rows.
        db.flush()

        still_unversioned = db.query(StationReference).filter(StationReference.rule_set_version.is_(None)).count()
        if still_unversioned:
            raise RuntimeError(
                f"{still_unversioned} StationReference row(s) left without a rule_set_version after backfill."
            )

        db.commit()
        print(f"Seeded {len(RACE_RULE_SETS)} race rule set(s); backfilled {len(unversioned)} station row(s).")
    finally:
        db.close()


if __name__ == "__main__":
    run()
