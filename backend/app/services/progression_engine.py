"""Turns logged workout performance into a suggested load for the next time the athlete
sees the same movement.

**Method**: RPE-based autoregulation — a well-established strength-coaching method (the
athlete's own reported effort decides whether load goes up, holds, or backs off, rather
than a fixed percentage table read off a chart). Named plainly here so it's clear this is
standard practice, not something invented for this app.

Triggered synchronously right after a workout is logged (`PATCH /workouts/{id}/log`),
mirroring the pattern `recovery_engine.py` already uses elsewhere in this codebase: log
something -> immediately recompute -> mutate a stored future week. Same precedent, different
target field (`suggested_load_kg` on a future `Workout.prescription` block, rather than
`TrainingWeek.actual_intensity`).

A movement's *first* occurrence in a block naturally gets no suggestion — there's nothing to
build from yet. That's fine: this app never needed upfront 1RM testing at onboarding: it
bootstraps working loads entirely from the athlete's own first logged session.

Conditioning (AMRAP/rounds) is handled separately and more conservatively: round counts are
emergent under max effort, so this only surfaces a same-format comparison
(`previous_rounds_completed`/`previous_rpe`) rather than algorithmically changing the target.
Auto-adjusting an AMRAP's time/rep target is a real design question that deserves its own
pass, not a guessed rule.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models import Workout
from app.schemas.training import BlockLog, ConditioningLog, WorkoutLogUpdate

# At or below this RPE, the athlete had room to spare -> nudge load up. At or above the hold
# threshold, they were near max effort -> hold rather than add. Between the two, still hold
# (no clear signal either way) — conservative by design, since HYROX training compounds
# fatigue across many movement patterns in a way a single-lift program doesn't.
RPE_INCREASE_THRESHOLD = 7.0
RPE_HOLD_THRESHOLD = 9.0
LOAD_INCREASE_PCT = 0.025  # conservative +2.5%, the low end of typical autoregulated jumps


def apply_progression(db: Session, workout: Workout, payload: WorkoutLogUpdate) -> None:
    """Call right after `workout.logged_result` has been saved. Looks ahead within the same
    training block for the next not-yet-reached occurrence of each logged movement/format on
    the same day-of-week slot, and annotates it in place."""

    week = workout.week
    block = week.block if week else None
    if block is None:
        return

    future_weeks = sorted(
        (w for w in block.weeks if w.week_number > week.week_number),
        key=lambda w: w.week_number,
    )
    if not future_weeks:
        return

    changed = False
    for block_log in payload.blocks:
        if _apply_strength_progression(workout, block_log, future_weeks):
            changed = True

    if payload.conditioning is not None:
        if _apply_conditioning_comparison(workout, payload.conditioning, future_weeks):
            changed = True

    if changed:
        db.commit()


def _movement_at_index(workout: Workout, index: int) -> Optional[str]:
    blocks = (workout.prescription or {}).get("blocks") or []
    if 0 <= index < len(blocks):
        return blocks[index].get("movement")
    return None


def _apply_strength_progression(workout: Workout, block_log: BlockLog, future_weeks: list) -> bool:
    movement = _movement_at_index(workout, block_log.index)
    if not movement or not block_log.sets or block_log.rpe is None:
        return False

    last_weight = next((s.weight_kg for s in reversed(block_log.sets) if s.weight_kg is not None), None)
    if last_weight is None:
        return False

    target = _find_next_matching_block(future_weeks, workout.day_of_week, movement)
    if target is None:
        return False
    future_workout, future_block = target

    if block_log.rpe <= RPE_INCREASE_THRESHOLD:
        future_block["suggested_load_kg"] = round(last_weight * (1 + LOAD_INCREASE_PCT), 1)
        future_block["progression_note"] = (
            f"Last time: {last_weight:g}kg @ RPE {block_log.rpe:g} — you had room, nudged up."
        )
    else:
        future_block["suggested_load_kg"] = last_weight
        reason = "RPE was near max" if block_log.rpe >= RPE_HOLD_THRESHOLD else "close to max effort"
        future_block["progression_note"] = f"Last time: {last_weight:g}kg @ RPE {block_log.rpe:g} — holding, {reason}."

    flag_modified(future_workout, "prescription")
    return True


def _find_next_matching_block(future_weeks: list, day_of_week: int, movement: str):
    for week in future_weeks:
        for future_workout in week.workouts:
            if future_workout.day_of_week != day_of_week:
                continue
            for block in (future_workout.prescription or {}).get("blocks") or []:
                if block.get("movement") == movement:
                    return future_workout, block
    return None


def _apply_conditioning_comparison(workout: Workout, conditioning_log: ConditioningLog, future_weeks: list) -> bool:
    conditioning = (workout.prescription or {}).get("conditioning")
    if not isinstance(conditioning, dict) or conditioning.get("format") not in ("amrap", "rounds"):
        return False

    target = _find_next_matching_conditioning(future_weeks, workout.day_of_week, conditioning["format"])
    if target is None:
        return False
    future_workout, future_conditioning = target

    if conditioning_log.rounds_completed is not None:
        future_conditioning["previous_rounds_completed"] = conditioning_log.rounds_completed
    if conditioning_log.extra_reps is not None:
        future_conditioning["previous_extra_reps"] = conditioning_log.extra_reps
    if conditioning_log.rpe is not None:
        future_conditioning["previous_rpe"] = conditioning_log.rpe

    flag_modified(future_workout, "prescription")
    return True


def _find_next_matching_conditioning(future_weeks: list, day_of_week: int, fmt: str):
    for week in future_weeks:
        for future_workout in week.workouts:
            if future_workout.day_of_week != day_of_week:
                continue
            conditioning = (future_workout.prescription or {}).get("conditioning")
            if isinstance(conditioning, dict) and conditioning.get("format") == fmt:
                return future_workout, conditioning
    return None
