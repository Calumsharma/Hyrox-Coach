"""The 15 CapabilityMetric rows — Program Engine v5 Milestone 1B, plan §C.

All quantitative. Evidence classes graded conservatively: only VO2max's relationship to HYROX
performance is research_supported (Brandt et al. 2025); every other metric — including every
station diagnostic — is coach_derived, since spec §7's station pathway model is explicitly a
coaching hypothesis, and official race-load/rule-set data being versioned elsewhere
(RaceRuleSet/StationReference) does not make a capability *interpretation* built on top of it
research-validated. No CapabilityBandPolicy/CapabilityConfidencePolicy rows are seeded
alongside these — those start empty, per the plan.

CapabilityMetric is an immutable seed definition — this seed function only ever inserts rows
that don't yet exist; it never updates one in place.
"""

from app.db import SessionLocal
from app.models import CapabilityMetric
from app.models.enums import StationSlug

CAPABILITY_METRICS = [
    {
        "id": "vo2max_wearable_ml_kg_min",
        "capability_id": "aerobic_capacity",
        "station": None,
        "unit": "ml_kg_min",
        "higher_is_better": True,
        "evidence_class": "research_supported",
        "description": "VO2max as reported by a connected wearable (RecoveryReading is "
        "provider-neutral — Apple Health, Garmin, WHOOP or another normalized source).",
    },
    {
        "id": "threshold_pace_riegel_sec_per_km",
        "capability_id": "threshold_race_pace",
        "station": None,
        "unit": "sec_per_km",
        "higher_is_better": False,
        "evidence_class": "coach_derived",
        "description": "Threshold pace estimated from a 5K/10K benchmark time via Riegel's formula.",
    },
    {
        "id": "long_run_late_pace_decay_pct",
        "capability_id": "running_economy_durability",
        "station": None,
        "unit": "pct",
        "higher_is_better": False,
        "evidence_class": "coach_derived",
        "description": "Percentage pace decay across the back half of a logged long run.",
    },
    {
        "id": "post_station_split_penalty_sec_per_km",
        "capability_id": "compromised_running",
        "station": None,
        "unit": "sec_per_km",
        "higher_is_better": False,
        "evidence_class": "coach_derived",
        "description": "Pace penalty on the run immediately following a race station, from race splits.",
    },
    {
        "id": "relative_strength_squat_1rm_per_bodyweight",
        "capability_id": "max_relative_strength",
        "station": None,
        "unit": "ratio",
        "higher_is_better": True,
        "evidence_class": "coach_derived",
        "description": "Back squat 1RM expressed relative to bodyweight.",
    },
    {
        "id": "strength_endurance_rep_decay_pct",
        "capability_id": "strength_endurance",
        "station": None,
        "unit": "pct",
        "higher_is_better": False,
        "evidence_class": "coach_derived",
        "description": "Rep-quality decay across a logged strength session's working sets.",
    },
    {
        "id": "sled_push_race_load_split_sec",
        "capability_id": "station_economy",
        "station": StationSlug.SLED_PUSH.value,
        "unit": "sec",
        "higher_is_better": False,
        "evidence_class": "coach_derived",
        "description": "Sled push split time at race-equivalent load.",
    },
    {
        "id": "sled_pull_race_load_split_sec",
        "capability_id": "station_economy",
        "station": StationSlug.SLED_PULL.value,
        "unit": "sec",
        "higher_is_better": False,
        "evidence_class": "coach_derived",
        "description": "Sled pull split time at race-equivalent load.",
    },
    {
        "id": "skierg_1000m_time_sec",
        "capability_id": "station_economy",
        "station": StationSlug.SKIERG.value,
        "unit": "sec",
        "higher_is_better": False,
        "evidence_class": "coach_derived",
        "description": "SkiErg 1000m time.",
    },
    {
        "id": "row_1000m_time_sec",
        "capability_id": "station_economy",
        "station": StationSlug.ROW.value,
        "unit": "sec",
        "higher_is_better": False,
        "evidence_class": "coach_derived",
        "description": "Rowing 1000m time.",
    },
    {
        "id": "wall_ball_100rep_time_sec",
        "capability_id": "station_economy",
        "station": StationSlug.WALL_BALLS.value,
        "unit": "sec",
        "higher_is_better": False,
        "evidence_class": "coach_derived",
        "description": "Time to complete 100 wall balls at race-equivalent load/target.",
    },
    {
        "id": "wall_ball_no_rep_count",
        "capability_id": "station_economy",
        "station": StationSlug.WALL_BALLS.value,
        "unit": "count",
        "higher_is_better": False,
        "evidence_class": "coach_derived",
        "description": "Number of no-reps (missed target) across a wall-ball set.",
    },
    {
        "id": "farmers_carry_race_load_split_sec",
        "capability_id": "grip_postural_endurance",
        "station": StationSlug.FARMERS_CARRY.value,
        "unit": "sec",
        "higher_is_better": False,
        "evidence_class": "coach_derived",
        "description": "Farmers carry split time at race-equivalent load.",
    },
    {
        "id": "dead_hang_time_sec",
        "capability_id": "grip_postural_endurance",
        "station": None,
        "unit": "sec",
        "higher_is_better": True,
        "evidence_class": "coach_derived",
        "description": "Dead-hang time-to-failure benchmark.",
    },
    {
        "id": "pacing_split_delta_pct",
        "capability_id": "pacing_execution",
        "station": None,
        "unit": "pct",
        "higher_is_better": False,
        "evidence_class": "coach_derived",
        "description": "Early-to-late kilometre split variance across a run or race.",
    },
]


def run():
    db = SessionLocal()
    try:
        inserted = 0
        for row in CAPABILITY_METRICS:
            if db.get(CapabilityMetric, row["id"]) is None:
                db.add(CapabilityMetric(**row))
                inserted += 1
        db.commit()
        print(f"Seeded {inserted} new capability metric(s) ({len(CAPABILITY_METRICS)} total in seed set).")
    finally:
        db.close()


if __name__ == "__main__":
    run()
