"""Individualized running pace targets, derived from the athlete's own 5K/10K times.

Nothing like this existed before this file: `predicted_5k_seconds`/`current_10k_seconds`
were collected at onboarding and never read by any service. Two pieces, both standard,
publicly documented endurance-coaching tools rather than anything proprietary to any coach
or app:

1. Riegel's formula (Riegel, P.S., "Athletic Records and Human Endurance", American
   Scientist, 1981) predicts an equivalent race time at a different distance from a known
   one: T2 = T1 * (D2/D1)^1.06. Used here only to fill in whichever of 5K/10K the athlete
   didn't report, never to invent a time from nothing.
2. Training paces are computed as documented, approximate offsets from race pace — a
   long-standing endurance-coaching heuristic (easy/long-run pace sits meaningfully slower
   than 10K pace, threshold work sits close to 10K pace, short reps sit close to 5K pace).
   These are deliberately conservative, clearly-labeled approximations, not lab-tested
   individual prescriptions (that would need a real fitness test, e.g. a lactate profile).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.models import Athlete

RIEGEL_EXPONENT = 1.06
FIVE_K_METERS = 5000.0
TEN_K_METERS = 10000.0

# Training-pace offsets from 10K pace, in seconds per km. Approximate, documented
# endurance-coaching heuristics — not sport-science-lab-tested numbers. Long-run pace sits
# slightly slower than daily easy pace (same aerobic intent, but held for much longer, so a
# more conservative effort), not faster.
EASY_PACE_OFFSET_SEC_PER_KM = 60.0
LONG_RUN_PACE_OFFSET_SEC_PER_KM = 75.0


@dataclass
class PaceProfile:
    five_k_pace_sec_per_km: float
    ten_k_pace_sec_per_km: float
    easy_pace_sec_per_km: float
    threshold_pace_sec_per_km: float
    interval_pace_sec_per_km: float
    long_run_pace_sec_per_km: float


def predict_equivalent_time(known_seconds: float, known_meters: float, target_meters: float) -> float:
    """Riegel's formula: T2 = T1 * (D2/D1)^1.06."""
    return known_seconds * (target_meters / known_meters) ** RIEGEL_EXPONENT


def resolve_pace_profile(athlete: Athlete) -> Optional[PaceProfile]:
    """Builds a PaceProfile from whichever of the athlete's 5K/10K times exist, cross-predicting
    the missing one via Riegel. Returns None if the athlete has reported neither — unlike max HR
    (which always has the Tanaka age-based fallback), there's no honest way to estimate a pace
    without at least one real data point, so we simply omit pace targets rather than guess.
    """
    five_k = athlete.predicted_5k_seconds
    ten_k = athlete.current_10k_seconds

    if five_k is None and ten_k is None:
        return None
    if five_k is None:
        five_k = predict_equivalent_time(ten_k, TEN_K_METERS, FIVE_K_METERS)
    if ten_k is None:
        ten_k = predict_equivalent_time(five_k, FIVE_K_METERS, TEN_K_METERS)

    five_k_pace = five_k / (FIVE_K_METERS / 1000.0)
    ten_k_pace = ten_k / (TEN_K_METERS / 1000.0)

    return PaceProfile(
        five_k_pace_sec_per_km=five_k_pace,
        ten_k_pace_sec_per_km=ten_k_pace,
        easy_pace_sec_per_km=ten_k_pace + EASY_PACE_OFFSET_SEC_PER_KM,
        threshold_pace_sec_per_km=ten_k_pace,
        interval_pace_sec_per_km=five_k_pace,
        long_run_pace_sec_per_km=ten_k_pace + LONG_RUN_PACE_OFFSET_SEC_PER_KM,
    )


_PACE_ZONE_FIELD = {
    "easy": "easy_pace_sec_per_km",
    "threshold": "threshold_pace_sec_per_km",
    "interval": "interval_pace_sec_per_km",
    "long_run": "long_run_pace_sec_per_km",
}


def pace_for_zone(profile: PaceProfile, zone: str) -> Optional[int]:
    field = _PACE_ZONE_FIELD.get(zone)
    if field is None:
        return None
    return round(getattr(profile, field))
