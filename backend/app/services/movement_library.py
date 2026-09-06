"""Encodes the athlete's real 8-week HYROX program (their own PT-designed template,
shared during planning) as reusable, tier-scaled session archetypes.

Each archetype is a function `(tier) -> prescription dict` shaped as:
    {"warm_up": [str, ...], "blocks": [{...}], "conditioning": {...}, "cool_down": [str, ...]?}

Sourced directly from the user's Week 1 (load), Week 4 (deload), and Week 8 (taper)
screenshots. Where a tier/week-kind combination wasn't shown (e.g. Advanced wasn't
captured for every session), the nearest observed pattern is extrapolated one step
further and flagged with a comment — these are the first things to correct once more
of the real program is available, not confident values.
"""

from __future__ import annotations

from app.models.enums import ExperienceTier

# ---------------------------------------------------------------------------
# Warm-ups, reused across sessions by category.
# ---------------------------------------------------------------------------

WARM_UPS = {
    "dynamic_strength": [
        "3-5 min bike (30 sec uptempo / 30 sec easy)",
        "10 air squats",
        "10 bootstrap squats",
        "8 world's greatest stretch (per side)",
        "10 alternating reverse lunges",
        "10 90-90 stretch",
    ],
    "running_drills": [
        "20 sec skipping",
        "20 high knees",
        "20 sec A-skips",
        "10 calf raises",
        "(2 rounds)",
    ],
    "run_row_primer": [
        "5-10 min light run (build gradually to Zone 2 pace)",
        "3 min row (30 sec uptempo / 30 sec easy x 3 rounds)",
        "3 x 100m running strides (fast, not sprinting)",
        "10 leg swings (per side)",
        "10 lateral leg swings (per side)",
    ],
    "run_row_ski_primer": [
        "5-10 min easy run (gradually build to slightly faster pace if possible)",
        "2 min row (30 sec uptempo / 30 sec easy x 2 rounds)",
        "2 min ski (30 sec uptempo / 30 sec easy x 2 rounds)",
        "10 bodyweight walking lunges",
        "10 leg swings (per side)",
    ],
    "loaded_station_primer": [
        "2 rounds: 2 min cycle (30 sec easy / 30 sec uptempo)",
        "10 heel-elevated bodyweight squats",
        "8 thread-the-needle (per side)",
        "30 sec dead hang",
        "10 PVC or band pass-throughs",
    ],
    "intervals_primer": [
        "5-10 min light run (gradually build to Zone 2 pace)",
        "3 x 100m running strides (fast, not sprinting)",
        "10 leg swings (per side)",
        "10 lateral leg swings (per side)",
        "10 air squats",
    ],
    "race_day_warmup": [
        "5-10 min easy jog",
        "3 x 100m strides",
        "3 x 100m row (slightly faster than race pace)",
        "3 x 100m ski (slightly faster than race pace)",
    ],
}

RACE_DAY_MOBILITY = [
    "90-90 stretches",
    "Bootstrap squats",
    "Leg swings",
    "Lateral leg swings",
    "World's greatest stretch",
]

MOBILITY_FLOW = [
    "Cat-Cow: 10 reps",
    "World's Greatest Stretch: 10 reps per side",
    "Active Alternating Calf Stretch: 20 reps",
    "90-90 Stretch: 10 reps",
    "Thread the Needle: 10 reps per side",
    "Prayer Stretch: 30 sec",
    "(2-3 rounds)",
]


def _tier_pick(tier: ExperienceTier, beginner, intermediate, advanced):
    return {
        ExperienceTier.BEGINNER: beginner,
        ExperienceTier.INTERMEDIATE: intermediate,
        ExperienceTier.ADVANCED: advanced,
    }[tier]


# ---------------------------------------------------------------------------
# Load-week archetypes (base/build/peak weeks)
# ---------------------------------------------------------------------------

def full_body_strength_conditioning(tier: ExperienceTier) -> dict:
    """Day 1 style: main strength blocks (fixed across tiers) + an overloaded conditioning finisher."""
    return {
        "warm_up": WARM_UPS["dynamic_strength"],
        "blocks": [
            {"movement": "barbell_front_squat", "sets": 4, "reps": 5, "rest_sec": 75},
            {"movement": "hex_bar_deadlift", "sets": 4, "reps": 5, "rest_sec": 75},
            {"movement": "incline_db_bench_press", "sets": 4, "reps": 5, "rest_sec": 75},
            {"movement": "db_thruster", "sets": 4, "reps": 10, "rest_sec": 75},
        ],
        "conditioning": {
            "format": "amrap",
            "duration_min": 15,
            "movements": [
                "20 cal ski",
                "8 barbell alternating reverse lunge",
                "20 cal echo bike",
                "15 wall balls (heavier than race weight)",
            ],
        },
    }


def easy_run_core(tier: ExperienceTier) -> dict:
    """Day 2 / Day 23 style: Zone 2 run + a core circuit, both tier-scaled by duration/hold time."""
    run_minutes = _tier_pick(tier, "30-35", "35-40", "40-45")
    plank_seconds = _tier_pick(tier, 60, 75, 90)
    rest_seconds = _tier_pick(tier, 60, 60, 45)
    return {
        "warm_up": WARM_UPS["running_drills"],
        "blocks": [
            {"movement": "zone_2_run", "duration_min": run_minutes},
            {
                "movement": "core_circuit",
                "sets": 3,
                "detail": f"Low plank {plank_seconds}s, high plank {plank_seconds}s, high plank shoulder taps {plank_seconds}s",
                "rest_sec": rest_seconds,
            },
        ],
        "conditioning": None,
    }


def run_row_intervals(tier: ExperienceTier) -> dict:
    """Day 3 style: pyramid run intervals into a race-pace/faster-than-race-pace combo, then row intervals."""
    long_rep_m = _tier_pick(tier, 1200, 1400, 1600)
    finisher_m = _tier_pick(tier, 300, 400, 500)
    return {
        "warm_up": WARM_UPS["run_row_primer"],
        "blocks": [
            {"movement": "run_intervals", "detail": f"2 x {long_rep_m}m @ comfortably hard pace, 1 min walk rest"},
            {"movement": "run_intervals", "detail": "4 x 800m @ faster than HYROX pace, 1 min walk rest"},
            {"movement": "run_intervals", "detail": f"1 x 1000m @ race pace, immediately into {finisher_m}m @ faster than race pace, 3-4 min rest"},
            {"movement": "row_intervals", "detail": "2 x 1000m row, 2 min rest — round 1 at 1-2 sec/500m faster than race pace, round 2 at race pace"},
        ],
        "conditioning": None,
    }


def station_rotation(tier: ExperienceTier, focus_stations: list[str]) -> dict:
    """Day 4 style loaded-station day. `focus_stations` (2-3 slugs) is chosen by the engine,
    biased toward the athlete's weaknesses instead of a plain round-robin."""
    farmers_minutes = _tier_pick(tier, 1.5, 2, 2)
    return {
        "warm_up": WARM_UPS["loaded_station_primer"],
        "blocks": [
            {"movement": "goblet_squat", "sets": 3, "reps": 15, "rest_sec": 30, "note": "build into speed and full ROM"},
            *_station_blocks(focus_stations, farmers_minutes),
            {"movement": "db_bench_lat_pullover", "sets": 3, "reps": 12, "rest_sec": 75},
            {"movement": "pull_ups", "sets": 3, "reps": 6, "rest_sec": 75, "note": "banded if needed"},
        ],
        "conditioning": {"format": "steady_aerobic", "duration_min": "15-20", "movement": "cycle"},
    }


def _station_blocks(focus_stations: list[str], farmers_minutes: float) -> list[dict]:
    blocks = []
    for slug in focus_stations:
        if slug == "sled_push":
            blocks.append({"movement": "sled_push", "sets": 4, "distance_m": 20, "rest_sec": 60, "note": "heavier than race weight"})
        elif slug == "sled_pull":
            blocks.append({"movement": "sled_pull", "sets": 4, "distance_m": 20, "rest_sec": 60, "note": "heavier than race weight"})
        elif slug == "farmers_carry":
            blocks.append({"movement": "farmers_carry", "sets": 2, "duration_min": farmers_minutes, "note": "@ race weight, as fast and as far as possible"})
        elif slug == "sandbag_lunges":
            blocks.append({"movement": "sandbag_walking_lunges", "sets": 2, "duration_min": 2, "note": "@ race weight — set 1 as fast as possible, set 2 sustainable beyond duration"})
        elif slug == "wall_balls":
            blocks.append({"movement": "wall_ball_touches", "detail": "2 rounds: 45m walking lunge, 45 wall balls"})
    return blocks


def hyrox_interval_training(tier: ExperienceTier) -> dict:
    """Day 6 style: race-station circuit at pace. Advanced round count (5) is extrapolated
    from the beginner(3)/intermediate(4) pattern — not directly observed."""
    rounds = _tier_pick(tier, 3, 4, 5)
    return {
        "warm_up": WARM_UPS["run_row_ski_primer"],
        "blocks": [
            {"movement": "run", "distance_m": 800, "note": "strong / controlled"},
        ],
        "conditioning": {
            "format": "rounds",
            "rounds": rounds,
            "rest_sec": 120,
            "movements": [
                "20 wall balls",
                "20 walking lunges (DB front rack)",
                "400m run @ faster than race pace",
                "25m burpee broad jumps",
            ],
        },
    }


def long_aerobic_run(tier: ExperienceTier) -> dict:
    """Day 7 style. Advanced range (55-60) is extrapolated from the beginner/intermediate
    step size — the load-week Advanced number wasn't captured directly."""
    run_range = _tier_pick(tier, "45-50", "50-55", "55-60")
    return {
        "warm_up": WARM_UPS["running_drills"],
        "blocks": [
            {"movement": "zone_2_run", "duration_min": run_range, "note": "optional: 4 min run / 1 min walk, repeat until total time reached"},
        ],
        "conditioning": None,
    }


def deload_long_aerobic_run(tier: ExperienceTier) -> dict:
    """Day 28 style: reduced running volume vs the load week, with Intermediate/Advanced
    getting easy cycling added back — trading impact volume for low-impact aerobic volume."""
    run_range = _tier_pick(tier, "35-45", "45-55", "55-65")
    blocks = [{"movement": "zone_2_run", "duration_min": run_range, "note": "optional: 4 min run / 1 min walk, repeat until total time reached"}]
    if tier != ExperienceTier.BEGINNER:
        blocks.append({"movement": "zone_2_cycle", "duration_min": 15, "note": "maintain Zone 2 heart rate"})
    return {"warm_up": WARM_UPS["running_drills"], "blocks": blocks, "conditioning": None}


def active_recovery() -> dict:
    """Day 5 style — identical every week, no tier scaling."""
    return {
        "warm_up": [],
        "blocks": [
            {"movement": "optional_active_recovery", "detail": "Light cycling, walking, or gentle mobility — easy and non-fatiguing"},
            {"movement": "mobility_flow", "detail": ", ".join(MOBILITY_FLOW)},
        ],
        "conditioning": None,
        "cool_down": ["Slow, controlled breathing and gentle stretching"],
    }


# ---------------------------------------------------------------------------
# Deload-week archetypes (real content swaps, not just a lower number)
# ---------------------------------------------------------------------------

def deload_strength(tier: ExperienceTier) -> dict:
    """Day 22 style: same lifts/order as the load week, fewer sets at higher reps,
    no overloaded conditioning finisher — just easy aerobic or an easy erg AMRAP."""
    run_range = _tier_pick(tier, "20-25", "25-30", "30-35")
    return {
        "warm_up": WARM_UPS["dynamic_strength"],
        "blocks": [
            {"movement": "barbell_front_squat", "sets": 3, "reps": 10, "rest_sec": 75, "note": "higher reps this week — reduce load vs previous weeks"},
            {"movement": "hex_bar_deadlift", "sets": 3, "reps": 10, "rest_sec": 75},
            {"movement": "incline_db_bench_press", "sets": 3, "reps": 10, "rest_sec": 75},
            {"movement": "db_thruster", "sets": 3, "reps": 10, "rest_sec": 75},
        ],
        "conditioning": {
            "format": "choice",
            "options": [
                {"movement": "zone_2_run", "duration_min": run_range},
                {"format": "amrap_alternative", "movements": ["1000m ski", "1000m row", "50 cal assault bike"]},
            ],
        },
    }


def deload_station_rotation(tier: ExperienceTier) -> dict:
    """Day 25 style: loaded station work is dropped entirely this week, replaced by
    faster-than-race-pace run+erg intervals."""
    finisher_min = _tier_pick(tier, 15, 20, 20)
    return {
        "warm_up": WARM_UPS["loaded_station_primer"],
        "blocks": [
            {"movement": "run", "distance_m": 1000, "note": "build into Zone 4 pace, 90 sec rest"},
            {"movement": "run_ski_intervals", "detail": "2 rounds: 800m run (faster than race pace), 800m ski, 2 min rest"},
            {"movement": "run_row_intervals", "detail": "2 rounds: 800m run (faster than race pace), 800m row, 2 min rest"},
        ],
        "conditioning": {"format": "amrap", "duration_min": finisher_min, "movements": ["3 min ski", "3 min row", "3 min assault/echo bike"]},
    }


# ---------------------------------------------------------------------------
# Taper-week archetypes (final week before the event)
# ---------------------------------------------------------------------------

def taper_strength(tier: ExperienceTier) -> dict:
    """Day 50 style: unilateral/bodyweight-biased work, no heavy bilateral barbell lifts
    this close to race day. Advanced isn't directly observed — reuses Intermediate's numbers."""
    sets = _tier_pick(tier, 3, 4, 4)
    run_range = _tier_pick(tier, "15-20", "20-25", "20-25")
    return {
        "warm_up": WARM_UPS["dynamic_strength"],
        "blocks": [
            {"movement": "bulgarian_split_squat", "sets": sets, "reps": 10, "unit": "per side", "rest_sec": 90},
            {"movement": "pull_ups", "sets": sets, "reps": "5-10", "rest_sec": 60},
            {"movement": "sissy_squat", "sets": 3, "reps": 10, "tempo": "3-0-1-0", "rest_sec": 90, "paired_with": "db_or_barbell_rdl"},
            {"movement": "db_or_barbell_rdl", "sets": 3, "reps": 10, "rest_sec": 90},
            {"movement": "bent_over_barbell_row", "sets": 3, "reps": 10, "rest_sec": 90, "paired_with": "kettlebell_swings"},
            {"movement": "kettlebell_swings", "sets": 3, "reps": 20, "rest_sec": 90},
        ],
        "conditioning": {
            "format": "choice",
            "options": [{"movement": "zone_2_run", "duration_min": run_range}, {"format": "mixed_machine_amrap"}],
        },
    }


def race_run_through() -> dict:
    """Day 51 — full run-through of the race at race weight and race pacing. No tiering."""
    return {
        "warm_up": WARM_UPS["run_row_ski_primer"],
        "blocks": [{"movement": "full_race_run_through", "note": "Final run through of all race stations. Use race weight and race pacing."}],
        "conditioning": None,
    }


def ski_row_run_touch(tier: ExperienceTier) -> dict:
    """Day 52 — a brief (1 min each) touch of all 8 official race stations plus running,
    at low volume, to prime every movement pattern without accumulating fatigue."""
    run_minutes = _tier_pick(tier, 1, 2, 2)
    return {
        "warm_up": WARM_UPS["run_row_ski_primer"],
        "blocks": [{"movement": "run", "distance_m": 1000, "note": "@ race pace"}],
        "conditioning": {
            "format": "rounds",
            "rounds": 3,
            "rest_sec": 120,
            "movements": [
                "1 min ski", "1 min sled push", "1 min sled pull", "1 min burpee broad jumps",
                f"{run_minutes} min run", "1 min rower", "1 min farmer's carry", "1 min sandbag walking lunge", "1 min wall balls",
            ],
        },
    }


def taper_easy_aerobic(tier: ExperienceTier) -> dict:
    """Day 53 — easy aerobic maintenance, athlete's choice of modality."""
    run_range = _tier_pick(tier, "25-30", "30-40", "40-45")
    return {
        "warm_up": WARM_UPS["running_drills"],
        "blocks": [{"movement": "easy_aerobic", "duration_min": run_range, "note": "options: easy run, cycle, erg machines, or a mix"}],
        "conditioning": None,
    }


def by_feel_rest() -> dict:
    """Day 54 (pre-race) and, absent other guidance, Day 56 (day after race) — no fixed
    prescription, athlete's own judgment call."""
    return {
        "warm_up": [],
        "blocks": [
            {"movement": "full_rest", "note": "OR optional light activity based on what you feel you need: stretching, easy walk, light cycle"},
        ],
        "conditioning": None,
        "by_feel": True,
    }


def race_day_warmup() -> dict:
    """Day 55 — the race-morning warm-up protocol itself, not a training session."""
    return {
        "warm_up": WARM_UPS["race_day_warmup"],
        "blocks": [{"movement": "mobility_dynamic_stretches", "detail": ", ".join(RACE_DAY_MOBILITY)}],
        "conditioning": None,
    }
