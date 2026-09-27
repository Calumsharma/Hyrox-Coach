"""CapabilityGap orchestration — Program Engine v5 Milestone 2, plan §D5/§D7.

Corrected `CapabilityGap` logical identity (plan §D5, point 5): `(athlete_id, metric_id,
based_on_score_id, band_policy_id_or_sentinel, band_policy_version_or_sentinel,
gap_computation_method)` — not merely `(athlete_id, metric_id, based_on_score_id)`, which would
collide if the same score is later reinterpreted under a new or revised band policy.

`band_policy_id_or_sentinel`/`band_policy_version_or_sentinel` reflect the policy that was
actually EVALUATED, not just the resulting classification: the stable sentinel pair
`("no_policy", "0")` is used only when no `CapabilityBandPolicy` exists at all for the metric
(always true in Milestone 2 production, since zero rows are ever seeded); whenever a real policy
DOES exist and is evaluated — reachable only via a synthetic test fixture in this milestone —
the identity carries that policy's real `(id, version)`, **even if the classification result is
"unclassified"** (the score simply fell into no band). Collapsing every "unclassified" outcome
onto the same sentinel regardless of which policy produced it was a real bug: it made "no
policy", "policy v1, no matching band", and "policy v2, no matching band" collide onto one gap
id, silently discarding whichever evaluation didn't insert first. The database `band_policy_id`
column still correctly stays NULL whenever `classification="unclassified"` (Milestone 1B's own
CHECK requires this) — only the identity hash, not the stored column, carries the extra state.

`gap_computation_method="gap_v1"` is the versioned seam a future milestone uses to fold
confidence-policy identity in (bumping to `"gap_v2"`) without redesigning this tuple.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models import CapabilityBandPolicy, CapabilityGap, CapabilityScore
from app.services.capability_classification import classify_score_against_band_policy
from app.services.capability_db_compat import idempotent_insert
from app.services.capability_identity import deterministic_id

GAP_COMPUTATION_METHOD = "gap_v1"
NO_POLICY_SENTINEL = ("no_policy", "0")

# No confidence evaluator exists this milestone (plan §D7). If a real band policy DOES exist and
# DOES classify (only reachable via a synthetic test fixture — production seeds zero policies),
# the CapabilityGap CHECK constraint requires confidence != 'none' whenever classification !=
# 'unclassified'. This is the one placeholder confidence value assigned in that hypothetical
# path — deliberately the lowest non-none tier, since no real confidence semantics exist to
# justify anything higher.
_PLACEHOLDER_CLASSIFIED_CONFIDENCE = "low"


def _latest_band_policy(db: Session, metric_id: str) -> Optional[CapabilityBandPolicy]:
    return (
        db.query(CapabilityBandPolicy)
        .filter(CapabilityBandPolicy.metric_id == metric_id)
        .order_by(CapabilityBandPolicy.version.desc())
        .first()
    )


def _reasoning_text(classification: str, band_policy: Optional[CapabilityBandPolicy]) -> str:
    if band_policy is None:
        return "No CapabilityBandPolicy exists yet for this metric — classification cannot be produced."
    if classification == "unclassified":
        return f"Score did not fall within any band of policy version {band_policy.version}."
    return f"Classified against CapabilityBandPolicy version {band_policy.version}."


def compute_gap(db: Session, athlete_id: str, metric_id: str, score: Optional[CapabilityScore]) -> Optional[CapabilityGap]:
    """Returns None (writes nothing) when `score` is None — `CapabilityGap.based_on_score_id` is
    NOT NULL by design (Milestone 1B): "no data at all" is no row, never a null-score row."""
    if score is None:
        return None

    band_policy = _latest_band_policy(db, metric_id)
    if band_policy is None:
        classification = "unclassified"
        confidence = "none"
        band_policy_id = None
        band_policy_identity = NO_POLICY_SENTINEL
    else:
        classification = classify_score_against_band_policy(db, score, band_policy)
        # Corrected identity bug: the deterministic identity must reflect the actual policy that
        # was EVALUATED, even when the result is "unclassified" (the score fell into no band).
        # Collapsing to NO_POLICY_SENTINEL here — the old behavior — made "no policy exists",
        # "policy v1 evaluated, no matching band", and "policy v2 evaluated, no matching band"
        # collide onto the same gap id, silently discarding the later two policy evaluations'
        # real reasoning text behind whichever one happened to insert first. The database
        # `band_policy_id` column still correctly stays NULL for `unclassified` (Milestone 1B's
        # own CHECK requires it), even though the identity hash now carries the real policy state.
        band_policy_identity = (band_policy.id, str(band_policy.version))
        if classification == "unclassified":
            confidence = "none"
            band_policy_id = None
        else:
            confidence = _PLACEHOLDER_CLASSIFIED_CONFIDENCE
            band_policy_id = band_policy.id

    gap_id = deterministic_id(
        "capability_gaps",
        athlete_id,
        metric_id,
        score.id,
        band_policy_identity[0],
        band_policy_identity[1],
        GAP_COMPUTATION_METHOD,
    )

    values = dict(
        id=gap_id,
        athlete_id=athlete_id,
        metric_id=metric_id,
        classification=classification,
        confidence=confidence,
        based_on_score_id=score.id,
        band_policy_id=band_policy_id,
        reasoning=_reasoning_text(classification, band_policy),
        flagged_for_reassessment=False,
        flag_reason=None,
        computed_at=datetime.utcnow(),
    )
    return idempotent_insert(db, CapabilityGap, values)
