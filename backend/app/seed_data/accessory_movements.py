"""Seed library of training movements, tagged by which HYROX station weakness they address.

Kept intentionally small for v1 — enough for the program engine to have real
material per weakness. Expand over time rather than front-loading every possible drill.
"""

from app.models.enums import StationSlug

ACCESSORY_MOVEMENTS = [
    # Strength base (Wendler 5/3/1 style) — underpins sled, lunges, carries.
    {"id": "back_squat", "name": "Back Squat", "category": "strength",
     "addresses_stations": [StationSlug.SLED_PUSH, StationSlug.SANDBAG_LUNGES], "notes": "5/3/1 main lift"},
    {"id": "deadlift", "name": "Deadlift", "category": "strength",
     "addresses_stations": [StationSlug.SLED_PULL, StationSlug.FARMERS_CARRY], "notes": "5/3/1 main lift"},
    {"id": "overhead_press", "name": "Overhead Press", "category": "strength",
     "addresses_stations": [StationSlug.WALL_BALLS, StationSlug.SKIERG], "notes": "5/3/1 main lift"},
    {"id": "bench_press", "name": "Bench Press", "category": "strength",
     "addresses_stations": [StationSlug.BURPEE_BROAD_JUMP], "notes": "5/3/1 main lift"},

    # Station-specific skill/strength.
    {"id": "sled_push_repeats", "name": "Sled Push Repeats", "category": "strength",
     "addresses_stations": [StationSlug.SLED_PUSH], "notes": "Race-load and overload variations"},
    {"id": "sled_pull_repeats", "name": "Sled Pull Repeats", "category": "strength",
     "addresses_stations": [StationSlug.SLED_PULL], "notes": "Race-load and overload variations"},
    {"id": "farmers_carry_intervals", "name": "Farmers Carry Intervals", "category": "strength",
     "addresses_stations": [StationSlug.FARMERS_CARRY], "notes": "Grip and carry endurance under fatigue"},
    {"id": "weighted_lunges", "name": "Weighted Walking Lunges", "category": "strength",
     "addresses_stations": [StationSlug.SANDBAG_LUNGES], "notes": "Sandbag or dumbbell loaded"},
    {"id": "wall_ball_emom", "name": "Wall Ball EMOM", "category": "strength",
     "addresses_stations": [StationSlug.WALL_BALLS], "notes": "Muscular endurance under time pressure"},
    {"id": "erg_intervals", "name": "SkiErg / Row Intervals", "category": "aerobic",
     "addresses_stations": [StationSlug.SKIERG, StationSlug.ROW], "notes": "Pacing and aerobic power for erg stations"},
    {"id": "burpee_broad_jump_repeats", "name": "Burpee Broad Jump Repeats", "category": "strength",
     "addresses_stations": [StationSlug.BURPEE_BROAD_JUMP], "notes": "Anaerobic capacity and movement efficiency"},

    # Running — HYROX's real differentiator is running while pre-fatigued.
    {"id": "compromised_run", "name": "Compromised Running", "category": "run",
     "addresses_stations": [], "notes": "Run intervals immediately after a station to train pacing under fatigue"},
    {"id": "aerobic_base_run", "name": "Aerobic Base Run", "category": "run",
     "addresses_stations": [], "notes": "Easy-paced volume, builds the aerobic ceiling everything else sits on"},
    {"id": "hyrox_pace_intervals", "name": "HYROX-Pace Run Intervals", "category": "run",
     "addresses_stations": [], "notes": "1km repeats at goal race pace"},

    {"id": "mobility_flow", "name": "Mobility / Recovery Flow", "category": "mobility",
     "addresses_stations": [], "notes": "General mobility, used on recovery-adjusted lighter days"},
]
