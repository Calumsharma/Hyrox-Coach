from datetime import date

from app.models import Athlete, ProgrammeDecision, RaceRuleSet
from app.models.enums import EvidenceClass, ProgrammeDecisionType


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
