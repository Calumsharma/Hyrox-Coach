"""The 10 abstract CapabilityDefinition rows — Program Engine v5 Milestone 1B.

Slug set and descriptions per spec §4.1 and the Milestone 1B plan's Decision 1 (grip_postural_
endurance and pacing_execution kept in scope alongside the eight your message named directly).
CapabilityDefinition is an immutable seed definition (see app/models/capability.py) — this
seed function only ever inserts rows that don't yet exist; it never updates one in place.
"""

from app.db import SessionLocal
from app.models import CapabilityDefinition

CAPABILITY_DEFINITIONS = [
    {
        "id": "aerobic_capacity",
        "name": "Aerobic Capacity",
        "description": "Ability to accumulate sustainable work over the full race duration.",
        "measurement_hint": "VO2max, easy-run durability, HR drift.",
    },
    {
        "id": "threshold_race_pace",
        "name": "Threshold & Race Pace",
        "description": "Sustainable speed at high aerobic demand.",
        "measurement_hint": "5K/10K data, a real threshold test, race-run splits.",
    },
    {
        "id": "running_economy_durability",
        "name": "Running Economy & Durability",
        "description": "Ability to preserve pace as fatigue grows over a run.",
        "measurement_hint": "Pace/HR relationship, late-run pace decay.",
    },
    {
        "id": "compromised_running",
        "name": "Compromised Running",
        "description": "Ability to regain running pace after a station.",
        "measurement_hint": "Post-station split loss and recovery distance.",
    },
    {
        "id": "max_relative_strength",
        "name": "Maximal / Relative Strength",
        "description": "Force reserve above what race-load stations require.",
        "measurement_hint": "A real strength test, expressed relative to body mass.",
    },
    {
        "id": "strength_endurance",
        "name": "Strength Endurance",
        "description": "Repeated submaximal force output under fatigue.",
        "measurement_hint": "Rep and split decay across sets.",
    },
    {
        "id": "station_economy",
        "name": "Station Economy",
        "description": "Technique and energy cost at each of the 8 race stations.",
        "measurement_hint": "Time, stroke rate, breaks, no-reps, pacing consistency per station.",
    },
    {
        "id": "grip_postural_endurance",
        "name": "Grip & Postural Endurance",
        "description": "Carry/pull capacity and trunk position under load.",
        "measurement_hint": "Grip test, carry breaks, sled-pull mechanics.",
    },
    {
        "id": "tissue_capacity",
        "name": "Tissue Capacity",
        "description": "Tolerance of running, jumping, lunging, and loading. Never scored from "
        "CapabilityAssessment data — captured only via AthleteStatusReport, which the "
        "capability-scoring pipeline never reads (Milestone 1B Decision 1/A7).",
        "measurement_hint": "Recent exposure, self-reported symptoms, injury history.",
    },
    {
        "id": "pacing_execution",
        "name": "Pacing & Execution",
        "description": "Ability to distribute effort across the race.",
        "measurement_hint": "Early-to-late split change, transition time.",
    },
]


def run():
    db = SessionLocal()
    try:
        inserted = 0
        for row in CAPABILITY_DEFINITIONS:
            if db.get(CapabilityDefinition, row["id"]) is None:
                db.add(CapabilityDefinition(**row))
                inserted += 1
        db.commit()
        print(f"Seeded {inserted} new capability definition(s) ({len(CAPABILITY_DEFINITIONS)} total in seed set).")
    finally:
        db.close()


if __name__ == "__main__":
    run()
