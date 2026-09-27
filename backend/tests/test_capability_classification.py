"""General-purpose band classification — Program Engine v5 Milestone 2, plan §D7. Tested against
synthetic, never-seeded `CapabilityBandPolicy`/`CapabilityBand` fixtures. In production this
function is always queried against zero real rows (see test_capability_gap_service.py), so this
file is the only place a real (non-`unclassified`) classification is ever produced."""

from datetime import date, datetime

from app.models import (
    Athlete,
    CapabilityBand,
    CapabilityBandPolicy,
    CapabilityDefinition,
    CapabilityMetric,
    CapabilityScore,
)
from app.services.capability_classification import classify_score_against_band_policy


def _athlete(db_session):
    a = Athlete(email="classification@example.com")
    db_session.add(a)
    db_session.commit()
    return a


def _metric(db_session, metric_id="threshold_pace_riegel_sec_per_km", capability_id="threshold_race_pace"):
    db_session.add(CapabilityDefinition(id=capability_id, name=capability_id, description="", measurement_hint=""))
    db_session.commit()
    m = CapabilityMetric(
        id=metric_id, capability_id=capability_id, station=None, unit="sec_per_km",
        higher_is_better=False, evidence_class="coach_derived", description="",
    )
    db_session.add(m)
    db_session.commit()
    return m


def _score(db_session, athlete, metric, value):
    s = CapabilityScore(
        athlete_id=athlete.id, metric_id=metric.id, value=value,
        computation_method="test_v1", evidence_class="coach_derived", computed_at=datetime(2026, 9, 1),
    )
    db_session.add(s)
    db_session.commit()
    return s


def _band_policy_with_bands(db_session, metric):
    """weak: (310, +inf); adequate: [280, 310); strong: (-inf, 280) — lower pace is better."""
    policy = CapabilityBandPolicy(metric_id=metric.id, version=1, effective_from=date(2026, 9, 1), notes="test fixture — never seeded")
    db_session.add(policy)
    db_session.commit()
    db_session.add_all([
        CapabilityBand(band_policy_id=policy.id, label="strong", lower_bound=None, upper_bound=280, upper_inclusive=False, sort_order=0),
        CapabilityBand(band_policy_id=policy.id, label="adequate", lower_bound=280, lower_inclusive=True, upper_bound=310, upper_inclusive=False, sort_order=1),
        CapabilityBand(band_policy_id=policy.id, label="weak", lower_bound=310, lower_inclusive=True, upper_bound=None, sort_order=2),
    ])
    db_session.commit()
    return policy


def test_no_policy_is_unclassified(db_session):
    athlete = _athlete(db_session)
    metric = _metric(db_session)
    score = _score(db_session, athlete, metric, 300.0)

    assert classify_score_against_band_policy(db_session, score, None) == "unclassified"


def test_value_inside_strong_band(db_session):
    athlete = _athlete(db_session)
    metric = _metric(db_session)
    policy = _band_policy_with_bands(db_session, metric)
    score = _score(db_session, athlete, metric, 270.0)

    assert classify_score_against_band_policy(db_session, score, policy) == "strong"


def test_value_inside_adequate_band_inclusive_lower_bound(db_session):
    athlete = _athlete(db_session)
    metric = _metric(db_session)
    policy = _band_policy_with_bands(db_session, metric)
    score = _score(db_session, athlete, metric, 280.0)  # exactly the inclusive lower bound

    assert classify_score_against_band_policy(db_session, score, policy) == "adequate"


def test_value_inside_weak_band(db_session):
    athlete = _athlete(db_session)
    metric = _metric(db_session)
    policy = _band_policy_with_bands(db_session, metric)
    score = _score(db_session, athlete, metric, 350.0)

    assert classify_score_against_band_policy(db_session, score, policy) == "weak"


def test_value_outside_every_band_is_unclassified_not_guessed(db_session):
    """A pathological policy where every band is exclusive at a shared boundary — the classifier
    never picks the "nearest" band for a value that falls in the gap."""
    athlete = _athlete(db_session)
    metric = _metric(db_session)
    policy = CapabilityBandPolicy(metric_id=metric.id, version=1, effective_from=date(2026, 9, 1), notes="gap fixture")
    db_session.add(policy)
    db_session.commit()
    db_session.add(CapabilityBand(band_policy_id=policy.id, label="strong", lower_bound=None, upper_bound=280, upper_inclusive=False, sort_order=0))
    db_session.commit()
    score = _score(db_session, athlete, metric, 280.0)  # exactly the exclusive boundary — inside no band

    assert classify_score_against_band_policy(db_session, score, policy) == "unclassified"
