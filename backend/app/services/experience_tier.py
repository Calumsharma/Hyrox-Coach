"""Suggests an athlete's training experience tier from their race history.

User-confirmed rule, evaluated top-down (most-advanced check first, since a single
strong signal — a fast solo time or a lot of race experience — should be enough to
qualify someone as Advanced even if they're borderline on the other axis):

    Advanced:     best solo time <= 1:15:00  OR  total race count (incl. doubles) >= 5
    Intermediate: best solo time <= 1:30:00  AND  3 <= total race count <= 5
    Beginner:     everything else (the default)

This is only ever a *suggestion* — the athlete can override it at onboarding.
"""

from __future__ import annotations

from typing import Optional

from app.models import Athlete, PastHyroxResult
from app.models.enums import ExperienceTier, SOLO_DIVISIONS

ADVANCED_TIME_SECONDS = 75 * 60
INTERMEDIATE_TIME_SECONDS = 90 * 60
INTERMEDIATE_MIN_RACES = 3
INTERMEDIATE_MAX_RACES = 5
ADVANCED_MIN_RACES = 5


def suggest_tier_from_inputs(best_solo_time_seconds: Optional[int], race_count: int) -> ExperienceTier:
    if (best_solo_time_seconds is not None and best_solo_time_seconds <= ADVANCED_TIME_SECONDS) or race_count >= ADVANCED_MIN_RACES:
        return ExperienceTier.ADVANCED

    if (
        best_solo_time_seconds is not None
        and best_solo_time_seconds <= INTERMEDIATE_TIME_SECONDS
        and INTERMEDIATE_MIN_RACES <= race_count <= INTERMEDIATE_MAX_RACES
    ):
        return ExperienceTier.INTERMEDIATE

    return ExperienceTier.BEGINNER


def suggest_experience_tier(athlete: Athlete) -> ExperienceTier:
    race_count = len(athlete.past_results)
    solo_times = [r.total_time_seconds for r in athlete.past_results if r.division in SOLO_DIVISIONS]
    best_solo_time = min(solo_times) if solo_times else None
    return suggest_tier_from_inputs(best_solo_time, race_count)
