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
