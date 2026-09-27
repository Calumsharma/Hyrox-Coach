"""General-purpose, metric-agnostic band classification — Program Engine v5 Milestone 2, plan
§D7. Tested against synthetic (never-seeded) `CapabilityBandPolicy`/`CapabilityBand` fixtures;
queried in production against zero real rows, so every real classification this milestone is
`unclassified`. Confidence is not this function's concern — see `capability_gap_service.py`.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models import CapabilityBand, CapabilityBandPolicy, CapabilityScore


def classify_score_against_band_policy(
    db: Session, score: CapabilityScore, band_policy: Optional[CapabilityBandPolicy]
) -> str:
    """Returns one of "weak"/"adequate"/"strong"/"unclassified". `unclassified` when no policy
    exists, or when the score's value falls inside no band of an existing policy — the engine
    never guesses a nearest band."""
    if band_policy is None:
        return "unclassified"

    bands = db.query(CapabilityBand).filter(CapabilityBand.band_policy_id == band_policy.id).all()
    value = score.value
    for band in bands:
        lower_ok = band.lower_bound is None or (
            value >= band.lower_bound if band.lower_inclusive else value > band.lower_bound
        )
        upper_ok = band.upper_bound is None or (
            value <= band.upper_bound if band.upper_inclusive else value < band.upper_bound
        )
        if lower_ok and upper_ok:
            return band.label

    return "unclassified"
