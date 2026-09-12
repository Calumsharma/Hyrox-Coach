"""Builds the week-by-week planned intensity curve for a training block.

Four phases by proportion of the block: base -> build -> peak -> taper. Intensity is a
0-1 planned-load fraction (not a %1RM) used to scale volume/pace prescriptions when the
week's workouts are generated, and later as the baseline the recovery engine adjusts
around (Phase 3) — `planned_intensity` here is never rewritten once set; the recovery
engine only ever adjusts `actual_intensity` against it.
"""

from dataclasses import dataclass

PHASES = [
    ("base", 0.0, 0.4, 0.55, 0.72),
    ("build", 0.4, 0.75, 0.72, 0.88),
    ("peak", 0.75, 0.9, 0.88, 1.0),
    ("taper", 0.9, 1.0, 1.0, 0.55),
]

# Used for the *load-only* curve (see build_load_intensity_curve): base/build/peak with no
# internal taper phase, since taper is always handled by the block's explicit
# taper_week_numbers override, never by this curve. Without this, a load week landing at the
# end of its own progress range would get mislabeled "taper" and have its intensity dropped,
# even though it's really the last full-intensity build/peak week before the real taper.
LOAD_ONLY_PHASES = [
    ("base", 0.0, 0.4, 0.55, 0.72),
    ("build", 0.4, 0.75, 0.72, 0.88),
    ("peak", 0.75, 1.0, 0.88, 1.0),
]


@dataclass
class WeekPlan:
    week_number: int
    phase: str
    planned_intensity: float


def build_intensity_curve(length_weeks: int) -> list[WeekPlan]:
    if length_weeks < 1:
        raise ValueError("length_weeks must be >= 1")

    weeks: list[WeekPlan] = []
    for i in range(length_weeks):
        progress = i / (length_weeks - 1) if length_weeks > 1 else 1.0
        phase, intensity = _phase_and_intensity(progress, PHASES)
        weeks.append(WeekPlan(week_number=i + 1, phase=phase, planned_intensity=round(intensity, 3)))
    return weeks


def build_load_intensity_curve(load_week_count: int) -> list[WeekPlan]:
    """Like build_intensity_curve, but sized to only the block's *load* weeks (excluding
    deload/taper weeks) so the base->build->peak progression happens smoothly across weeks
    that actually carry load, regardless of which raw calendar week numbers they land on —
    a deload or taper week never "eats" a step of the progression."""

    if load_week_count < 1:
        return []

    weeks: list[WeekPlan] = []
    for i in range(load_week_count):
        progress = i / (load_week_count - 1) if load_week_count > 1 else 1.0
        phase, intensity = _phase_and_intensity(progress, LOAD_ONLY_PHASES)
        weeks.append(WeekPlan(week_number=i + 1, phase=phase, planned_intensity=round(intensity, 3)))
    return weeks


def _phase_and_intensity(progress: float, phases: list[tuple]) -> tuple[str, float]:
    for phase, start, end, intensity_start, intensity_end in phases:
        if progress <= end or phase == phases[-1][0]:
            span = end - start
            local_progress = (progress - start) / span if span > 0 else 1.0
            local_progress = max(0.0, min(1.0, local_progress))
            intensity = intensity_start + (intensity_end - intensity_start) * local_progress
            return phase, intensity
    raise AssertionError("unreachable")
