"""CapabilityGap orchestration — Program Engine v5 Milestone 2, plan §D5/§D7. Production always
queries zero real `CapabilityBandPolicy` rows, so every real gap this milestone is
`unclassified`/`none` — but the corrected identity tuple (point 5) must still append a new gap
whenever `based_on_score_id` changes, and must still no-op when it doesn't."""

from datetime import date, datetime

from app.models import Athlete, CapabilityBand, CapabilityBandPolicy, CapabilityDefinition, CapabilityMetric, CapabilityScore
from app.services.capability_gap_service import compute_gap


def _athlete(db_session):
    a = Athlete(email="gap-service@example.com")
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


def test_none_score_produces_no_gap(db_session):
    athlete = _athlete(db_session)
    metric = _metric(db_session)
    assert compute_gap(db_session, athlete.id, metric.id, None) is None


def test_no_policy_produces_unclassified_none_with_correct_reasoning(db_session):
    athlete = _athlete(db_session)
    metric = _metric(db_session)
    score = _score(db_session, athlete, metric, 300.0)

    gap = compute_gap(db_session, athlete.id, metric.id, score)
    assert gap.classification == "unclassified"
    assert gap.confidence == "none"
    assert gap.band_policy_id is None
    assert gap.based_on_score_id == score.id
    assert "No CapabilityBandPolicy exists yet" in gap.reasoning


def test_repeated_calls_with_same_score_are_a_true_noop(db_session):
    athlete = _athlete(db_session)
    metric = _metric(db_session)
    score = _score(db_session, athlete, metric, 300.0)

    gap1 = compute_gap(db_session, athlete.id, metric.id, score)
    gap2 = compute_gap(db_session, athlete.id, metric.id, score)

    assert gap1.id == gap2.id
    assert db_session.query(type(gap1)).count() == 1


def test_new_score_produces_new_gap_new_provenance(db_session):
    athlete = _athlete(db_session)
    metric = _metric(db_session)
    score1 = _score(db_session, athlete, metric, 300.0)
    score2 = _score(db_session, athlete, metric, 305.0)

    gap1 = compute_gap(db_session, athlete.id, metric.id, score1)
    gap2 = compute_gap(db_session, athlete.id, metric.id, score2)

    assert gap1.id != gap2.id
    assert gap1.based_on_score_id != gap2.based_on_score_id


def test_same_score_under_a_different_band_policy_version_appends_not_collides(db_session):
    """The exact fix for point 5: a policy change on the SAME score must produce a new gap, not
    silently collide with the earlier unclassified one."""
    athlete = _athlete(db_session)
    metric = _metric(db_session)
    score = _score(db_session, athlete, metric, 270.0)

    gap_no_policy = compute_gap(db_session, athlete.id, metric.id, score)
    assert gap_no_policy.classification == "unclassified"

    policy = CapabilityBandPolicy(metric_id=metric.id, version=1, effective_from=date(2026, 9, 1), notes="test fixture")
    db_session.add(policy)
    db_session.commit()
    db_session.add(CapabilityBand(band_policy_id=policy.id, label="strong", lower_bound=None, upper_bound=280, upper_inclusive=False, sort_order=0))
    db_session.commit()

    gap_with_policy = compute_gap(db_session, athlete.id, metric.id, score)

    assert gap_with_policy.id != gap_no_policy.id
    assert gap_with_policy.based_on_score_id == gap_no_policy.based_on_score_id == score.id
    assert gap_with_policy.classification == "strong"
    assert gap_with_policy.confidence != "none"
    assert gap_with_policy.band_policy_id == policy.id

    # Both gaps coexist — history is never overwritten.
    assert db_session.query(type(gap_no_policy)).filter_by(based_on_score_id=score.id).count() == 2


def test_no_policy_v1_unclassified_and_v2_unclassified_are_three_distinct_gaps(db_session):
    """The exact identity bug from independent review, point 4: when a real band policy exists
    but the score falls into NO band, the old code collapsed the identity to the same
    ("no_policy", "0") sentinel used for "no policy at all" — colliding across (a) no policy,
    (b) policy v1 evaluated but unclassified, and (c) policy v2 evaluated but unclassified. All
    three must be genuinely distinct gap rows, each carrying its own correct reasoning text —
    proving the fix doesn't just avoid a crash, but actually persists each evaluation's real
    reasoning rather than silently keeping whichever inserted first."""
    athlete = _athlete(db_session)
    metric = _metric(db_session)
    score = _score(db_session, athlete, metric, 999.0)  # deliberately outside every band below

    # (a) No policy at all.
    gap_no_policy = compute_gap(db_session, athlete.id, metric.id, score)
    assert gap_no_policy.classification == "unclassified"
    assert gap_no_policy.band_policy_id is None
    assert "No CapabilityBandPolicy exists yet" in gap_no_policy.reasoning

    # (b) Policy v1 exists and is evaluated, but the score (999.0) falls into no band (only a
    # narrow "strong" band below 280 is defined) — a real evaluation, still "unclassified".
    policy_v1 = CapabilityBandPolicy(metric_id=metric.id, version=1, effective_from=date(2026, 9, 1), notes="v1 fixture")
    db_session.add(policy_v1)
    db_session.commit()
    db_session.add(CapabilityBand(band_policy_id=policy_v1.id, label="strong", lower_bound=None, upper_bound=280, upper_inclusive=False, sort_order=0))
    db_session.commit()

    gap_v1_unclassified = compute_gap(db_session, athlete.id, metric.id, score)
    assert gap_v1_unclassified.classification == "unclassified"
    assert gap_v1_unclassified.band_policy_id is None  # DB column stays null per the CHECK
    assert f"policy version {policy_v1.version}" in gap_v1_unclassified.reasoning

    # (c) Policy v2 replaces it, also evaluated, also unclassified for this score.
    policy_v2 = CapabilityBandPolicy(metric_id=metric.id, version=2, effective_from=date(2026, 9, 2), notes="v2 fixture")
    db_session.add(policy_v2)
    db_session.commit()
    db_session.add(CapabilityBand(band_policy_id=policy_v2.id, label="strong", lower_bound=None, upper_bound=280, upper_inclusive=False, sort_order=0))
    db_session.commit()

    gap_v2_unclassified = compute_gap(db_session, athlete.id, metric.id, score)
    assert gap_v2_unclassified.classification == "unclassified"
    assert gap_v2_unclassified.band_policy_id is None
    assert f"policy version {policy_v2.version}" in gap_v2_unclassified.reasoning

    # All three are genuinely distinct rows — no collision, no identity collapsing.
    ids = {gap_no_policy.id, gap_v1_unclassified.id, gap_v2_unclassified.id}
    assert len(ids) == 3
    assert db_session.query(type(gap_no_policy)).filter_by(based_on_score_id=score.id).count() == 3

    # Each row's reasoning is genuinely its own — re-fetching from the DB (not the in-memory
    # return value) proves the correct text actually persisted, rather than an ID collision
    # silently discarding (b) or (c)'s insert behind (a)'s or each other's reasoning text.
    from app.models import CapabilityGap
    fetched_no_policy = db_session.get(CapabilityGap, gap_no_policy.id)
    fetched_v1 = db_session.get(CapabilityGap, gap_v1_unclassified.id)
    fetched_v2 = db_session.get(CapabilityGap, gap_v2_unclassified.id)
    assert "No CapabilityBandPolicy exists yet" in fetched_no_policy.reasoning
    assert f"policy version {policy_v1.version}" in fetched_v1.reasoning
    assert f"policy version {policy_v2.version}" in fetched_v2.reasoning
    assert fetched_v1.reasoning != fetched_v2.reasoning
