"""AthleteStatusReport — Program Engine v5 Milestone 1B. Model creation, the 3 CHECK
constraints (both directions), source-enum restriction, immutability, and confirmation that
nothing in this codebase auto-creates a report. No route/API test — none exists in 1B."""

from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Athlete, AthleteStatusReport
from app.models.immutability import ImmutableRecordError

REPO_ROOT = Path(__file__).resolve().parent.parent


def _athlete(db_session, email="status@example.com"):
    athlete = Athlete(email=email)
    db_session.add(athlete)
    db_session.commit()
    return athlete


def test_create_and_read(db_session):
    athlete = _athlete(db_session)
    report = AthleteStatusReport(
        athlete_id=athlete.id,
        recorded_at=datetime(2026, 9, 1),
        source="athlete_self_report",
        pain_present=True,
        symptom_severity="mild",
        body_area="left calf",
        illness_present=False,
        effect_on_training="reduced",
        notes="Tightness after Wednesday's session.",
    )
    db_session.add(report)
    db_session.commit()

    fetched = db_session.get(AthleteStatusReport, report.id)
    assert fetched.pain_present is True
    assert fetched.symptom_severity == "mild"
    assert fetched.effect_on_training == "reduced"


def test_no_pain_no_illness_defaults(db_session):
    athlete = _athlete(db_session)
    report = AthleteStatusReport(
        athlete_id=athlete.id,
        recorded_at=datetime(2026, 9, 1),
        source="athlete_self_report",
        pain_present=False,
        illness_present=False,
    )
    db_session.add(report)
    db_session.commit()

    fetched = db_session.get(AthleteStatusReport, report.id)
    assert fetched.symptom_severity is None
    assert fetched.effect_on_training is None


# --- CHECK 1: pain_present=false cannot coexist with a real symptom_severity ---

def test_no_pain_with_symptom_severity_is_rejected(db_session):
    athlete = _athlete(db_session)
    db_session.add(AthleteStatusReport(
        athlete_id=athlete.id, recorded_at=datetime(2026, 9, 1), source="athlete_self_report",
        pain_present=False, symptom_severity="moderate", illness_present=False,
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_no_pain_with_severity_none_is_accepted(db_session):
    athlete = _athlete(db_session)
    db_session.add(AthleteStatusReport(
        athlete_id=athlete.id, recorded_at=datetime(2026, 9, 1), source="athlete_self_report",
        pain_present=False, symptom_severity="none", illness_present=False,
    ))
    db_session.commit()


def test_pain_present_with_symptom_severity_is_accepted(db_session):
    athlete = _athlete(db_session)
    db_session.add(AthleteStatusReport(
        athlete_id=athlete.id, recorded_at=datetime(2026, 9, 1), source="athlete_self_report",
        pain_present=True, symptom_severity="severe", illness_present=False,
    ))
    db_session.commit()


# --- CHECK 2: effect_on_training in (reduced, avoid) requires pain_present or illness_present ---

def test_reduced_effect_without_pain_or_illness_is_rejected(db_session):
    athlete = _athlete(db_session)
    db_session.add(AthleteStatusReport(
        athlete_id=athlete.id, recorded_at=datetime(2026, 9, 1), source="athlete_self_report",
        pain_present=False, illness_present=False, effect_on_training="reduced",
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_avoid_effect_without_pain_or_illness_is_rejected(db_session):
    athlete = _athlete(db_session)
    db_session.add(AthleteStatusReport(
        athlete_id=athlete.id, recorded_at=datetime(2026, 9, 1), source="athlete_self_report",
        pain_present=False, illness_present=False, effect_on_training="avoid",
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_reduced_effect_with_illness_is_accepted(db_session):
    athlete = _athlete(db_session)
    db_session.add(AthleteStatusReport(
        athlete_id=athlete.id, recorded_at=datetime(2026, 9, 1), source="athlete_self_report",
        pain_present=False, illness_present=True, effect_on_training="reduced",
    ))
    db_session.commit()


# --- CHECK 3: no pain/illness at all -> effect_on_training must be none/null ---

def test_no_pain_no_illness_with_non_none_effect_is_rejected(db_session):
    # Covered structurally by CHECK 2 already (reduced/avoid require pain or illness), but this
    # asserts the third CHECK's own direction explicitly: pain_present/illness_present both
    # false permits only NULL or 'none' for effect_on_training.
    athlete = _athlete(db_session)
    db_session.add(AthleteStatusReport(
        athlete_id=athlete.id, recorded_at=datetime(2026, 9, 1), source="athlete_self_report",
        pain_present=False, illness_present=False, effect_on_training="avoid",
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_no_pain_no_illness_with_none_effect_is_accepted(db_session):
    athlete = _athlete(db_session)
    db_session.add(AthleteStatusReport(
        athlete_id=athlete.id, recorded_at=datetime(2026, 9, 1), source="athlete_self_report",
        pain_present=False, illness_present=False, effect_on_training="none",
    ))
    db_session.commit()


# --- source enum restriction ---

def test_source_rejects_value_outside_athlete_self_report_at_database_level(db_session):
    """The Python enum type is not, by itself, database enforcement — an independent audit
    correctly found that a direct insert with an arbitrary source string succeeded, since
    `source` is a plain String column. This asserts the actual CHECK constraint
    (ck_athlete_status_report_source) rejects it, not just that the enum has one member."""
    athlete = _athlete(db_session)

    db_session.add(AthleteStatusReport(
        athlete_id=athlete.id, recorded_at=datetime(2026, 9, 1), source="coach_entered_not_allowed",
        pain_present=False, illness_present=False,
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Session must still be usable, and the one legitimate value must still be accepted.
    report = AthleteStatusReport(
        athlete_id=athlete.id, recorded_at=datetime(2026, 9, 1), source="athlete_self_report",
        pain_present=False, illness_present=False,
    )
    db_session.add(report)
    db_session.commit()
    assert db_session.get(AthleteStatusReport, report.id) is not None


# --- Immutability ---

def test_creation_succeeds(db_session):
    athlete = _athlete(db_session)
    report = AthleteStatusReport(
        athlete_id=athlete.id, recorded_at=datetime(2026, 9, 1), source="athlete_self_report",
        pain_present=False, illness_present=False,
    )
    db_session.add(report)
    db_session.commit()
    assert db_session.get(AthleteStatusReport, report.id) is not None


def test_orm_update_is_rejected_and_row_unchanged(db_session):
    athlete = _athlete(db_session)
    report = AthleteStatusReport(
        athlete_id=athlete.id, recorded_at=datetime(2026, 9, 1), source="athlete_self_report",
        pain_present=True, illness_present=False, notes="original",
    )
    db_session.add(report)
    db_session.commit()
    report_id = report.id

    report.notes = "edited"
    with pytest.raises(ImmutableRecordError):
        db_session.commit()
    db_session.rollback()

    fetched = db_session.get(AthleteStatusReport, report_id)
    assert fetched.notes == "original"


def test_orm_delete_is_rejected_and_row_present(db_session):
    athlete = _athlete(db_session)
    report = AthleteStatusReport(
        athlete_id=athlete.id, recorded_at=datetime(2026, 9, 1), source="athlete_self_report",
        pain_present=False, illness_present=False,
    )
    db_session.add(report)
    db_session.commit()
    report_id = report.id

    db_session.delete(report)
    with pytest.raises(ImmutableRecordError):
        db_session.commit()
    db_session.rollback()

    assert db_session.get(AthleteStatusReport, report_id) is not None


def test_session_usable_after_rejected_update(db_session):
    athlete = _athlete(db_session)
    report = AthleteStatusReport(
        athlete_id=athlete.id, recorded_at=datetime(2026, 9, 1), source="athlete_self_report",
        pain_present=False, illness_present=False,
    )
    db_session.add(report)
    db_session.commit()

    report.pain_present = True
    try:
        db_session.commit()
    except ImmutableRecordError:
        db_session.rollback()

    other = Athlete(email="still-usable-status@example.com")
    db_session.add(other)
    db_session.commit()
    assert db_session.get(Athlete, other.id) is not None


# --- Nothing in this codebase reads or auto-creates an AthleteStatusReport in Milestone 1B ---

def test_no_production_code_references_athlete_status_report_outside_its_own_module():
    """Code-search check, not a route test (no route exists in 1B, per the plan). Confirms no
    service, route, or other production module reads AthleteStatusReport or writes to it
    outside the model's own file.

    Implemented as a plain Python source scan rather than `grep -rl`, per an independent audit:
    `grep -rl` over a directory can match generated `__pycache__/*.pyc` bytecode files (their
    binary content can still contain the class-name string), which is dialect-dependent
    (BSD/macOS vs. GNU grep handle binary-file matching differently) and fails on Linux. This
    scan only ever reads `*.py` source files under app/, so compiled bytecode is never
    considered regardless of platform or whether the suite has already generated it once.
    """
    app_dir = REPO_ROOT / "app"
    referencing_files = set()
    for py_file in app_dir.rglob("*.py"):
        if "AthleteStatusReport" in py_file.read_text(encoding="utf-8"):
            referencing_files.add(py_file.relative_to(REPO_ROOT).as_posix())

    allowed = {
        "app/models/athlete_status.py",
        "app/models/__init__.py",
        # Prose-only mentions (docstrings/seed descriptions explaining the design), not imports
        # or code usage — verified by direct read, not just this substring match.
        "app/models/enums.py",
        "app/seed_data/capabilities.py",
    }
    assert referencing_files <= allowed, f"Unexpected AthleteStatusReport reference(s): {referencing_files - allowed}"
