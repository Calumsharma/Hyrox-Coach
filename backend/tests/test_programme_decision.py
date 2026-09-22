from datetime import date

from app.models import Athlete, ProgrammeDecision, RaceRuleSet
from app.models.enums import EvidenceClass, ProgrammeDecisionType
from app.models.programme_decision import ProgrammeDecisionImmutableError


def test_create_and_read_programme_decision(db_session):
    athlete = Athlete(email="decision@example.com")
    rule_set = RaceRuleSet(
        id="hyrox_singles_2026_27",
        effective_from=date(2026, 1, 1),
        source_url="https://hyrox.com/rulebook/",
    )
    db_session.add_all([athlete, rule_set])
    db_session.commit()

    decision = ProgrammeDecision(
        athlete_id=athlete.id,
        decision_type=ProgrammeDecisionType.BASELINE_GENERATION,
        summary="Initial block generated.",
        before_state=None,
        after_state={"weeks": 8},
        schema_version="1",
        rule_set_version=rule_set.id,
        evidence_class=EvidenceClass.COACH_DERIVED,
    )
    db_session.add(decision)
    db_session.commit()

    fetched = db_session.get(ProgrammeDecision, decision.id)
    assert fetched is not None
    assert fetched.athlete_id == athlete.id
    assert fetched.decision_type == ProgrammeDecisionType.BASELINE_GENERATION
    assert fetched.after_state == {"weeks": 8}
    assert fetched.rule_set_version == "hyrox_singles_2026_27"
    assert fetched.evidence_class == EvidenceClass.COACH_DERIVED


def test_nullable_fields_default_correctly(db_session):
    athlete = Athlete(email="decision2@example.com")
    db_session.add(athlete)
    db_session.commit()

    decision = ProgrammeDecision(
        athlete_id=athlete.id,
        decision_type=ProgrammeDecisionType.MANUAL_COACH_EDIT,
    )
    db_session.add(decision)
    db_session.commit()

    fetched = db_session.get(ProgrammeDecision, decision.id)
    assert fetched.training_week_id is None
    assert fetched.athlete_session_id is None
    assert fetched.rule_set_version is None
    assert fetched.before_state is None
    assert fetched.after_state is None
    assert fetched.evidence_class == EvidenceClass.COACH_DERIVED  # column default
    assert fetched.schema_version == "1"


# --- Append-only enforcement (Milestone 1A hardening pass) ---
# The model docstring says "Never edited or deleted" — these tests prove that's actually
# enforced at the ORM level (via before_update/before_delete mapper events in
# app/models/programme_decision.py), not just documented.

def _make_decision(db_session, summary="Initial block generated."):
    athlete = Athlete(email=f"append-only-{summary}@example.com")
    db_session.add(athlete)
    db_session.commit()

    decision = ProgrammeDecision(
        athlete_id=athlete.id,
        decision_type=ProgrammeDecisionType.BASELINE_GENERATION,
        summary=summary,
    )
    db_session.add(decision)
    db_session.commit()
    return decision


def test_creation_succeeds(db_session):
    decision = _make_decision(db_session, summary="create-ok")
    assert db_session.get(ProgrammeDecision, decision.id) is not None


def test_orm_update_is_rejected_and_row_unchanged(db_session):
    decision = _make_decision(db_session, summary="update-original")
    decision_id = decision.id

    decision.summary = "update-attempted"
    try:
        db_session.commit()
        assert False, "expected ProgrammeDecisionImmutableError to be raised"
    except ProgrammeDecisionImmutableError:
        db_session.rollback()

    fetched = db_session.get(ProgrammeDecision, decision_id)
    assert fetched.summary == "update-original"


def test_orm_delete_is_rejected_and_row_present(db_session):
    decision = _make_decision(db_session, summary="delete-target")
    decision_id = decision.id

    db_session.delete(decision)
    try:
        db_session.commit()
        assert False, "expected ProgrammeDecisionImmutableError to be raised"
    except ProgrammeDecisionImmutableError:
        db_session.rollback()

    assert db_session.get(ProgrammeDecision, decision_id) is not None


def test_session_usable_after_rejected_update_and_delete(db_session):
    decision = _make_decision(db_session, summary="session-reuse")

    decision.summary = "blocked update"
    try:
        db_session.commit()
    except ProgrammeDecisionImmutableError:
        db_session.rollback()

    db_session.delete(decision)
    try:
        db_session.commit()
    except ProgrammeDecisionImmutableError:
        db_session.rollback()

    # The session must still be usable for ordinary work after two rejected operations.
    other = Athlete(email="still-usable@example.com")
    db_session.add(other)
    db_session.commit()
    assert db_session.get(Athlete, other.id) is not None

    another_decision = ProgrammeDecision(
        athlete_id=other.id,
        decision_type=ProgrammeDecisionType.MANUAL_COACH_EDIT,
        summary="created after rollback",
    )
    db_session.add(another_decision)
    db_session.commit()
    assert db_session.get(ProgrammeDecision, another_decision.id) is not None
