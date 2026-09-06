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
        phase, intensity = _phase_and_intensity(progress)
        weeks.append(WeekPlan(week_number=i + 1, phase=phase, planned_intensity=round(intensity, 3)))
    return weeks


def _phase_and_intensity(progress: float) -> tuple[str, float]:
    for phase, start, end, intensity_start, intensity_end in PHASES:
        if progress <= end or phase == PHASES[-1][0]:
            span = end - start
            local_progress = (progress - start) / span if span > 0 else 1.0
            local_progress = max(0.0, min(1.0, local_progress))
            intensity = intensity_start + (intensity_end - intensity_start) * local_progress
            return phase, intensity
    raise AssertionError("unreachable")
