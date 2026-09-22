import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Athlete, SchedulingConstraint


def test_create_and_read_scheduling_constraint(db_session):
    athlete = Athlete(email="scheduling@example.com")
    db_session.add(athlete)
    db_session.commit()

    constraint = SchedulingConstraint(
        athlete_id=athlete.id, day_of_week=2, available=False, notes="Work commitment every Wednesday."
    )
    db_session.add(constraint)
    db_session.commit()

    fetched = db_session.get(SchedulingConstraint, constraint.id)
    assert fetched is not None
    assert fetched.athlete_id == athlete.id
    assert fetched.day_of_week == 2
    assert fetched.available is False
    assert fetched.max_duration_minutes is None


def test_defaults_to_available_with_no_duration_cap(db_session):
    athlete = Athlete(email="scheduling2@example.com")
    db_session.add(athlete)
    db_session.commit()

    constraint = SchedulingConstraint(athlete_id=athlete.id, day_of_week=5)
    db_session.add(constraint)
    db_session.commit()

    fetched = db_session.get(SchedulingConstraint, constraint.id)
    assert fetched.available is True
    assert fetched.max_duration_minutes is None
    assert fetched.notes == ""


def test_multiple_constraints_per_athlete(db_session):
    athlete = Athlete(email="scheduling3@example.com")
    db_session.add(athlete)
    db_session.commit()

    db_session.add_all([
        SchedulingConstraint(athlete_id=athlete.id, day_of_week=0, max_duration_minutes=45),
        SchedulingConstraint(athlete_id=athlete.id, day_of_week=6, available=False),
    ])
    db_session.commit()

    rows = db_session.query(SchedulingConstraint).filter_by(athlete_id=athlete.id).all()
    assert len(rows) == 2
    assert {row.day_of_week for row in rows} == {0, 6}


# --- Validated constraints (Milestone 1A hardening pass) ---
# These enforce at the database level (unique constraint + check constraints, added in
# 0003_1a_hardening — see app/models/scheduling.py's __table_args__), so an ORM-level attempt
# to violate them must fail with IntegrityError, not just be caught by application code.

def test_duplicate_athlete_day_is_rejected(db_session):
    athlete = Athlete(email="scheduling-dupe@example.com")
    db_session.add(athlete)
    db_session.commit()

    db_session.add(SchedulingConstraint(athlete_id=athlete.id, day_of_week=3))
    db_session.commit()

    db_session.add(SchedulingConstraint(athlete_id=athlete.id, day_of_week=3, notes="second row, same day"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    rows = db_session.query(SchedulingConstraint).filter_by(athlete_id=athlete.id).all()
    assert len(rows) == 1


def test_day_of_week_outside_range_is_rejected(db_session):
    athlete = Athlete(email="scheduling-badday@example.com")
    db_session.add(athlete)
    db_session.commit()

    db_session.add(SchedulingConstraint(athlete_id=athlete.id, day_of_week=7))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    db_session.add(SchedulingConstraint(athlete_id=athlete.id, day_of_week=-1))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    assert db_session.query(SchedulingConstraint).filter_by(athlete_id=athlete.id).count() == 0


def test_zero_max_duration_is_rejected(db_session):
    athlete = Athlete(email="scheduling-zeroduration@example.com")
    db_session.add(athlete)
    db_session.commit()

    db_session.add(SchedulingConstraint(athlete_id=athlete.id, day_of_week=1, max_duration_minutes=0))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    assert db_session.query(SchedulingConstraint).filter_by(athlete_id=athlete.id).count() == 0


def test_negative_max_duration_is_rejected(db_session):
    athlete = Athlete(email="scheduling-negduration@example.com")
    db_session.add(athlete)
    db_session.commit()

    db_session.add(SchedulingConstraint(athlete_id=athlete.id, day_of_week=1, max_duration_minutes=-15))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    assert db_session.query(SchedulingConstraint).filter_by(athlete_id=athlete.id).count() == 0
