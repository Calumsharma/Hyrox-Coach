"""Heart-rate zone calculation.

Max HR uses the athlete's own tested value when they have one, falling back to the Tanaka
formula (208 - 0.7*age) — chosen over the older 220-age rule because it's the more accurate,
more current standard in the sports-science literature, at zero extra cost to implement.

Zone boundaries (%HRmax) follow the standard 5-zone model used in the HYROX coaching
literature: Z1 recovery, Z2 aerobic base, Z3 tempo ("grey zone" — avoid living here), Z4
threshold, Z5 VO2max/anaerobic. See the physiology research notes in the project plan for
why the race itself lives almost entirely in Z4-Z5 while training volume should live in Z2.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.models import Athlete
from app.models.enums import HeartRateZone

ZONE_RANGES_PCT: dict[HeartRateZone, tuple[float, float]] = {
    HeartRateZone.Z1_RECOVERY: (0.50, 0.60),
    HeartRateZone.Z2_AEROBIC_BASE: (0.60, 0.70),
    HeartRateZone.Z3_TEMPO: (0.70, 0.80),
    HeartRateZone.Z4_THRESHOLD: (0.80, 0.90),
    HeartRateZone.Z5_ANAEROBIC: (0.90, 1.00),
}


def estimate_max_hr(age: Optional[int]) -> Optional[int]:
    if age is None:
        return None
    return round(208 - 0.7 * age)


def resolve_max_hr(athlete: Athlete) -> Optional[int]:
    if athlete.tested_max_hr is not None:
        return athlete.tested_max_hr
    return estimate_max_hr(athlete.age)


@dataclass
class ZoneTarget:
    zone: HeartRateZone
    low_bpm: Optional[int]
    high_bpm: Optional[int]
    low_pct: float
    high_pct: float


def zone_target(athlete: Athlete, zone: HeartRateZone) -> ZoneTarget:
    """Returns bpm bounds when max HR is resolvable, otherwise just the %HRmax range so the
    client can still show something meaningful (e.g. "60-70% max HR") without a number."""

    low_pct, high_pct = ZONE_RANGES_PCT[zone]
    max_hr = resolve_max_hr(athlete)
    if max_hr is None:
        return ZoneTarget(zone=zone, low_bpm=None, high_bpm=None, low_pct=low_pct, high_pct=high_pct)
    return ZoneTarget(
        zone=zone,
        low_bpm=round(max_hr * low_pct),
        high_bpm=round(max_hr * high_pct),
        low_pct=low_pct,
        high_pct=high_pct,
    )
