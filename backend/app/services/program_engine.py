"""Turns an athlete profile + block parameters into a full TrainingBlock of weeks and workouts.

Session structure comes from `app/services/movement_library.py` (informed by the athlete's
real coaching program and by published HYROX training structure — see that module's docstring
and `/Users/calumsharma/.claude/plans/happy-weaving-raven.md`, "Program Engine v2" and v3).
Deload/taper placement is explicit per block (coach's call, not a fixed ratio); the smooth
base/build/peak intensity curve still drives `planned_intensity` and the phase label for weeks
that are neither deload nor taper.

Per-athlete individualization is resolved once per block, here, from three sources, and
threaded down into `movement_library.py`'s archetype functions rather than baked into them:
`resolve_pace_profile` (real 5K/10K-derived running paces), `StationReference`'s official
per-division race loads (real numeric overload targets), and `AccessoryMovement` matched
against the athlete's ranked weakness (real weakness-specific strength-day content).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models import AccessoryMovement, Athlete, StationReference, TrainingBlock, TrainingWeek, Workout
from app.models.enums import Discipline, ExperienceTier, HeartRateZone, StationSlug, WorkoutType
from app.services import movement_library as lib
from app.services.heart_rate import zone_target
from app.services.pace import PaceProfile, pace_for_zone, resolve_pace_profile
from app.services.periodization import build_load_intensity_curve
from app.services.weakness import rank_weaknesses

# Stations where the reference program prescribes training load *above* race weight (see
# movement_library.py's "heavier than race weight" notes) — the others ("@ race weight") are
# deliberately not overloaded. Beginner still gets a small, real overload (the "heavier than
# race weight" note has never been tier-gated) but a conservative one; Advanced gets the most,
# consistent with progressively loading connective tissue as training age increases.
OVERLOAD_ELIGIBLE_STATIONS = {
    StationSlug.SLED_PUSH.value,
    StationSlug.SLED_PULL.value,
    StationSlug.WALL_BALLS.value,
}
TIER_OVERLOAD_MULTIPLIER = {
    ExperienceTier.BEGINNER: 1.05,
    ExperienceTier.INTERMEDIATE: 1.15,
    ExperienceTier.ADVANCED: 1.25,
}

# Deload/taper weeks aren't part of the load curve (see build_load_intensity_curve), so they
# get fixed, deliberately-low intensities of their own rather than borrowing a number from it.
DELOAD_INTENSITY = 0.50
TAPER_INTENSITY = 0.45
RACE_WEEK_INTENSITY = 0.35

# Tiers/phases where continuous threshold work replaces interval work — see the physiology
# research notes in the plan doc. Base-phase weeks stay purely aerobic-volume + light strides;
# threshold introduction is a build/peak-phase tool, and Beginners aren't given it at all
# (they need general strength/aerobic base first, per the user's own coaching judgment).
THRESHOLD_RUN_TIERS = {ExperienceTier.INTERMEDIATE, ExperienceTier.ADVANCED}
THRESHOLD_RUN_PHASES = {"build", "peak"}


class UnsupportedDisciplineError(ValueError):
    """Raised when asked to build a program for a discipline with no real builder yet.

    We deliberately don't fall back to a generic/fabricated program here — the whole point
    of this engine is that HYROX content came from a real coach's program, and pretending
    to have equivalent expertise for other sports would be dishonest. See Discipline enum.
    """

    def __init__(self, discipline: Discipline):
        self.discipline = discipline
        super().__init__(
            f"Programming for {discipline.value} isn't built yet — HYROX is the only "
            "fully supported discipline right now."
        )

# The five "loadable" stations that rotate through the Day 4-style station day in the
# reference program (SkiErg/Row/burpee broad jumps show up elsewhere, as erg/run work).
LOADABLE_STATIONS = [
    StationSlug.SLED_PUSH.value,
    StationSlug.SLED_PULL.value,
    StationSlug.FARMERS_CARRY.value,
    StationSlug.SANDBAG_LUNGES.value,
    StationSlug.WALL_BALLS.value,
]


def suggest_deload_weeks(length_weeks: int) -> list[int]:
    """Default suggestion only — the block's actual schedule is coach/athlete-set."""
    return list(range(4, length_weeks, 4))


def suggest_taper_weeks(length_weeks: int) -> list[int]:
    return [length_weeks] if length_weeks >= 4 else []


def generate_training_block(
    db: Session,
    athlete: Athlete,
    length_weeks: int,
    start_date: date,
    goal_event_date: date,
    goal_time_seconds: int,
    deload_week_numbers: Optional[list[int]] = None,
    taper_week_numbers: Optional[list[int]] = None,
    discipline: Discipline = Discipline.HYROX,
) -> TrainingBlock:
    """Dispatches to the builder for `discipline`. Only HYROX has one — see `UnsupportedDisciplineError`."""
    if discipline != Discipline.HYROX:
        raise UnsupportedDisciplineError(discipline)

    return _generate_hyrox_block(
        db=db,
        athlete=athlete,
        length_weeks=length_weeks,
        start_date=start_date,
        goal_event_date=goal_event_date,
        goal_time_seconds=goal_time_seconds,
        deload_week_numbers=deload_week_numbers,
        taper_week_numbers=taper_week_numbers,
    )


def _generate_hyrox_block(
    db: Session,
    athlete: Athlete,
    length_weeks: int,
    start_date: date,
    goal_event_date: date,
    goal_time_seconds: int,
    deload_week_numbers: Optional[list[int]],
    taper_week_numbers: Optional[list[int]],
) -> TrainingBlock:
    deload_weeks = set(deload_week_numbers if deload_week_numbers is not None else suggest_deload_weeks(length_weeks))
    taper_weeks = set(taper_week_numbers if taper_week_numbers is not None else suggest_taper_weeks(length_weeks))

    weaknesses = rank_weaknesses(athlete, top_n=3)
    tier = athlete.experience_tier or ExperienceTier.BEGINNER
    pace_profile = resolve_pace_profile(athlete)
    overload_lookup = _resolve_overload_lookup(db, athlete.division, tier)
    weakness_accessory = _resolve_weakness_accessory(db, weaknesses[0] if weaknesses else None)

    # The base->build->peak progression is computed over only the weeks that actually carry
    # load, so a deload or taper week never "eats" a step of the progression (see
    # build_load_intensity_curve's docstring) — this is what was producing programs that
    # jumped straight from a deload into peak-intensity training with no build ramp at all
    # on shorter blocks, exactly the kind of discontinuity that raises injury risk.
    load_week_numbers = [w for w in range(1, length_weeks + 1) if w not in deload_weeks and w not in taper_weeks]
    load_curve = build_load_intensity_curve(len(load_week_numbers))

    block = TrainingBlock(
        athlete_id=athlete.id,
        discipline=Discipline.HYROX,
        start_date=start_date,
        length_weeks=length_weeks,
        goal_event_date=goal_event_date,
        goal_time_seconds=goal_time_seconds,
        target_weaknesses=weaknesses,
        deload_week_numbers=sorted(deload_weeks),
        taper_week_numbers=sorted(taper_weeks),
    )
    db.add(block)
    db.flush()

    station_rotation_index = 0  # advances on every week with a station day (load AND deload)
    load_curve_index = 0  # advances only on true load weeks — indexes into load_curve
    for week_number in range(1, length_weeks + 1):
        is_final_week = week_number == length_weeks

        if week_number in taper_weeks:
            phase = "taper"
            planned_intensity = RACE_WEEK_INTENSITY if is_final_week else TAPER_INTENSITY
            workouts = _race_week(tier) if is_final_week else _taper_week(tier)
        elif week_number in deload_weeks:
            phase = "deload"
            planned_intensity = DELOAD_INTENSITY
            workouts = _deload_week(tier, weaknesses, station_rotation_index)
            station_rotation_index += 1
        else:
            week_plan = load_curve[load_curve_index]
            phase = week_plan.phase
            planned_intensity = week_plan.planned_intensity
            workouts = _load_week(tier, weaknesses, station_rotation_index, phase, overload_lookup, weakness_accessory)
            station_rotation_index += 1
            load_curve_index += 1

        _attach_targets(athlete, pace_profile, workouts)

        week = TrainingWeek(
            block_id=block.id,
            week_number=week_number,
            phase=phase,
            planned_intensity=planned_intensity,
            actual_intensity=planned_intensity,
        )
        db.add(week)
        db.flush()

        for workout_data in workouts:
            db.add(Workout(week_id=week.id, **workout_data))

    db.commit()
    db.refresh(block)
    return block


def _workout(day_of_week: int, workout_type: WorkoutType, title: str, prescription: dict) -> dict:
    return {"day_of_week": day_of_week, "workout_type": workout_type, "title": title, "prescription": prescription}


def _attach_targets(athlete: Athlete, pace_profile: Optional[PaceProfile], workouts: list[dict]) -> None:
    """Resolves every `target_hr_zone`/`target_pace_zone` tag in movement_library.py's output
    to real numbers for this specific athlete: bpm from tested max HR or Tanaka-estimated,
    pace from their own 5K/10K times (omitted entirely if they've reported neither — see
    `app/services/pace.py`)."""

    for workout in workouts:
        prescription = workout["prescription"]
        for block in prescription.get("blocks") or []:
            _tag_bpm(athlete, block)
            _tag_pace(pace_profile, block)
        conditioning = prescription.get("conditioning")
        if isinstance(conditioning, dict):
            for option in conditioning.get("options") or []:
                _tag_bpm(athlete, option)
                _tag_pace(pace_profile, option)


def _tag_bpm(athlete: Athlete, block: dict) -> None:
    zone_value = block.get("target_hr_zone")
    if not zone_value:
        return
    target = zone_target(athlete, HeartRateZone(zone_value))
    if target.low_bpm is not None:
        block["target_hr_bpm"] = [target.low_bpm, target.high_bpm]


def _tag_pace(pace_profile: Optional[PaceProfile], block: dict) -> None:
    zone_value = block.get("target_pace_zone")
    if not zone_value or pace_profile is None:
        return
    pace_sec = pace_for_zone(pace_profile, zone_value)
    if pace_sec is not None:
        block["target_pace_per_km_sec"] = pace_sec


def _resolve_overload_lookup(db: Session, division, tier: ExperienceTier) -> dict:
    """Real numeric overload targets (kg) for the stations the reference program prescribes
    training heavier than race weight, from `StationReference`'s official per-division loads.
    Returns {} (gracefully — no overload numbers shown, text note stays as the only guidance)
    when the athlete hasn't set a division yet."""
    if division is None:
        return {}
    division_key = division.value if hasattr(division, "value") else division
    multiplier = TIER_OVERLOAD_MULTIPLIER.get(tier, 1.0)
    lookup: dict[str, float] = {}
    stations = (
        db.query(StationReference)
        .filter(StationReference.slug.in_(OVERLOAD_ELIGIBLE_STATIONS))
        .all()
    )
    for station in stations:
        loads = (station.division_loads or {}).get(division_key)
        if not loads:
            continue
        base_kg = loads.get("load_kg")
        if base_kg is None:
            continue
        slug_value = station.slug.value if hasattr(station.slug, "value") else station.slug
        lookup[slug_value] = round(base_kg * multiplier, 1)
    return lookup


def _resolve_weakness_accessory(db: Session, weakest_station: Optional[str]) -> Optional[AccessoryMovement]:
    """The real `AccessoryMovement` (strength category) that addresses the athlete's #1 ranked
    weak station, if any — see movement_library.py's `full_body_strength_conditioning`."""
    if not weakest_station:
        return None
    candidates = db.query(AccessoryMovement).filter(AccessoryMovement.category == "strength").all()
    for movement in candidates:
        if weakest_station in (movement.addresses_stations or []):
            return movement
    return None


def _choose_focus_stations(rotation_index: int, weaknesses: list[str]) -> list[str]:
    """Biases the station-day rotation toward the athlete's weaknesses rather than a plain
    round-robin: the athlete's weakest loadable station appears every load week (not just its
    1-in-5 round-robin turn), while the round-robin slot keeps the rest in rotation over time."""
    rotating = LOADABLE_STATIONS[rotation_index % len(LOADABLE_STATIONS)]
    weakest_loadable = next((w for w in weaknesses if w in LOADABLE_STATIONS), None)
    if weakest_loadable is None or weakest_loadable == rotating:
        return [rotating]
    return [rotating, weakest_loadable]


def _station_day_title(focus_stations: list[str]) -> str:
    names = [StationSlug(slug).name.replace("_", " ").title() for slug in focus_stations]
    return " / ".join(names)


def _load_week(
    tier: ExperienceTier,
    weaknesses: list[str],
    load_week_index: int,
    phase: str,
    overload_lookup: Optional[dict] = None,
    weakness_accessory: Optional[AccessoryMovement] = None,
) -> list[dict]:
    focus_stations = _choose_focus_stations(load_week_index, weaknesses)

    use_threshold_run = tier in THRESHOLD_RUN_TIERS and phase in THRESHOLD_RUN_PHASES
    wednesday = (
        _workout(2, WorkoutType.RUN, "Threshold Run", lib.continuous_threshold_run(tier))
        if use_threshold_run
        else _workout(2, WorkoutType.RUN, "The Grind", lib.run_row_intervals(tier))
    )

    return [
        _workout(0, WorkoutType.STRENGTH, "Forge", lib.full_body_strength_conditioning(tier, weakness_accessory)),
        _workout(1, WorkoutType.AEROBIC, "Engine", lib.easy_run_core(tier)),
        wednesday,
        _workout(3, WorkoutType.STATION_SKILL, f"Load Day: {_station_day_title(focus_stations)}", lib.station_rotation(tier, focus_stations, overload_lookup)),
        _workout(4, WorkoutType.MOBILITY, "Reset", lib.active_recovery()),
        _workout(5, WorkoutType.STATION_SKILL, "Race Simulation", lib.hyrox_interval_training(tier)),
        _workout(6, WorkoutType.AEROBIC, "Long Haul", lib.long_aerobic_run(tier)),
    ]


def _deload_week(tier: ExperienceTier, weaknesses: list[str], load_week_index: int) -> list[dict]:
    focus_stations = _choose_focus_stations(load_week_index, weaknesses)
    return [
        _workout(0, WorkoutType.STRENGTH, "Forge — Deload", lib.deload_strength(tier)),
        _workout(1, WorkoutType.AEROBIC, "Engine", lib.easy_run_core(tier)),
        _workout(2, WorkoutType.RUN, "The Grind — Deload", lib.run_row_intervals(tier)),
        _workout(3, WorkoutType.STATION_SKILL, f"Load Day — Deload: {_station_day_title(focus_stations)}", lib.deload_station_rotation(tier)),
        _workout(4, WorkoutType.MOBILITY, "Reset", lib.active_recovery()),
        _workout(5, WorkoutType.STATION_SKILL, "Race Simulation — Deload", lib.hyrox_interval_training(tier)),
        _workout(6, WorkoutType.AEROBIC, "Long Haul — Deload", lib.deload_long_aerobic_run(tier)),
    ]


def _taper_week(tier: ExperienceTier) -> list[dict]:
    """A taper week that is NOT the final week of the block (only used if the block has more
    than one taper week) — no direct source content for this case, so it reuses the deload
    station pattern (no loaded work) and taper strength."""
    return [
        _workout(0, WorkoutType.STRENGTH, "Forge — Taper", lib.taper_strength(tier)),
        _workout(1, WorkoutType.AEROBIC, "Engine", lib.easy_run_core(tier)),
        _workout(2, WorkoutType.RUN, "The Grind — Taper", lib.run_row_intervals(tier)),
        _workout(3, WorkoutType.STATION_SKILL, "Load Day — Touch", lib.deload_station_rotation(tier)),
        _workout(4, WorkoutType.MOBILITY, "Reset", lib.active_recovery()),
        _workout(5, WorkoutType.STATION_SKILL, "Race Simulation — Touch", lib.hyrox_interval_training(tier)),
        _workout(6, WorkoutType.AEROBIC, "Easy Aerobic", lib.taper_easy_aerobic(tier)),
    ]


def _race_week(tier: ExperienceTier) -> list[dict]:
    return [
        _workout(0, WorkoutType.STRENGTH, "Full Body Strength & Aerobic", lib.taper_strength(tier)),
        _workout(1, WorkoutType.RUN, "Race Run Through", lib.race_run_through()),
        _workout(2, WorkoutType.STATION_SKILL, "Ski / Row / Run Intervals", lib.ski_row_run_touch(tier)),
        _workout(3, WorkoutType.AEROBIC, "Easy Aerobic", lib.taper_easy_aerobic(tier)),
        _workout(4, WorkoutType.REST, "Pre-Race Rest Day", lib.by_feel_rest()),
        _workout(5, WorkoutType.RACE_DAY, "Race Day (with warm-up)", lib.race_day_warmup()),
        _workout(6, WorkoutType.REST, "Day After Race", lib.by_feel_rest()),
    ]
