"""Turns an athlete profile + block parameters into a full TrainingBlock of weeks and workouts.

Built from the athlete's real PT-designed 8-week HYROX program (not a generic periodization
synthesis) — see `app/services/movement_library.py` for the actual session content and
`/Users/calumsharma/.claude/plans/happy-weaving-raven.md` ("Program Engine v2") for the
design rationale. Deload/taper placement is explicit per block (coach's call, not a fixed
ratio); the smooth base/build/peak intensity curve still drives `planned_intensity` and the
phase label for weeks that are neither deload nor taper.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Athlete, TrainingBlock, TrainingWeek, Workout
from app.models.enums import Discipline, ExperienceTier, StationSlug, WorkoutType
from app.services import movement_library as lib
from app.services.periodization import build_intensity_curve
from app.services.weakness import rank_weaknesses


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
    curve = build_intensity_curve(length_weeks)

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

    load_week_index = 0
    for week_plan in curve:
        week_number = week_plan.week_number
        is_final_week = week_number == length_weeks

        if week_number in taper_weeks:
            phase = "taper"
            workouts = _race_week(tier) if is_final_week else _taper_week(tier)
        elif week_number in deload_weeks:
            phase = "deload"
            workouts = _deload_week(tier, weaknesses, load_week_index)
            load_week_index += 1
        else:
            phase = week_plan.phase
            workouts = _load_week(tier, weaknesses, load_week_index)
            load_week_index += 1

        week = TrainingWeek(
            block_id=block.id,
            week_number=week_number,
            phase=phase,
            planned_intensity=week_plan.planned_intensity,
            actual_intensity=week_plan.planned_intensity,
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


def _load_week(tier: ExperienceTier, weaknesses: list[str], load_week_index: int) -> list[dict]:
    focus_stations = _choose_focus_stations(load_week_index, weaknesses)
    return [
        _workout(0, WorkoutType.STRENGTH, "Full Body Strength & Conditioning", lib.full_body_strength_conditioning(tier)),
        _workout(1, WorkoutType.AEROBIC, "Easy Run + Core", lib.easy_run_core(tier)),
        _workout(2, WorkoutType.RUN, "Run & Row Training", lib.run_row_intervals(tier)),
        _workout(3, WorkoutType.STATION_SKILL, _station_day_title(focus_stations), lib.station_rotation(tier, focus_stations)),
        _workout(4, WorkoutType.MOBILITY, "Active Recovery or Rest/Mobility", lib.active_recovery()),
        _workout(5, WorkoutType.STATION_SKILL, "HYROX Interval Training", lib.hyrox_interval_training(tier)),
        _workout(6, WorkoutType.AEROBIC, "Long Aerobic Run", lib.long_aerobic_run(tier)),
    ]


def _deload_week(tier: ExperienceTier, weaknesses: list[str], load_week_index: int) -> list[dict]:
    focus_stations = _choose_focus_stations(load_week_index, weaknesses)
    return [
        _workout(0, WorkoutType.STRENGTH, "Strength Training + Easy Aerobic", lib.deload_strength(tier)),
        _workout(1, WorkoutType.AEROBIC, "Easy Run + Core", lib.easy_run_core(tier)),
        _workout(2, WorkoutType.RUN, "Intervals + Easy Ergs", lib.run_row_intervals(tier)),
        _workout(3, WorkoutType.STATION_SKILL, f"Station Performance + Cycle ({_station_day_title(focus_stations)})", lib.deload_station_rotation(tier)),
        _workout(4, WorkoutType.MOBILITY, "Active Recovery or Rest/Mobility", lib.active_recovery()),
        _workout(5, WorkoutType.STATION_SKILL, "HYROX Endurance", lib.hyrox_interval_training(tier)),
        _workout(6, WorkoutType.AEROBIC, "Long Aerobic Run", lib.deload_long_aerobic_run(tier)),
    ]


def _taper_week(tier: ExperienceTier) -> list[dict]:
    """A taper week that is NOT the final week of the block (only used if the block has more
    than one taper week) — no direct source content for this case, so it reuses the deload
    station pattern (no loaded work) and taper strength."""
    return [
        _workout(0, WorkoutType.STRENGTH, "Taper Strength", lib.taper_strength(tier)),
        _workout(1, WorkoutType.AEROBIC, "Easy Run + Core", lib.easy_run_core(tier)),
        _workout(2, WorkoutType.RUN, "Run & Row Training (reduced)", lib.run_row_intervals(tier)),
        _workout(3, WorkoutType.STATION_SKILL, "Station Touch + Cycle", lib.deload_station_rotation(tier)),
        _workout(4, WorkoutType.MOBILITY, "Active Recovery or Rest/Mobility", lib.active_recovery()),
        _workout(5, WorkoutType.STATION_SKILL, "HYROX Touch", lib.hyrox_interval_training(tier)),
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
