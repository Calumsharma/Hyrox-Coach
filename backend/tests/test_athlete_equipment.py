from app.models import Athlete, AthleteEquipmentProfile


def test_create_and_read_equipment_profile(db_session):
    athlete = Athlete(email="equipment@example.com")
    db_session.add(athlete)
    db_session.commit()

    profile = AthleteEquipmentProfile(athlete_id=athlete.id, available_equipment=["sled", "skierg", "wall_ball"])
    db_session.add(profile)
    db_session.commit()

    fetched = db_session.get(AthleteEquipmentProfile, athlete.id)
    assert fetched is not None
    assert fetched.available_equipment == ["sled", "skierg", "wall_ball"]
    assert fetched.updated_at is not None


def test_defaults_to_empty_equipment_list(db_session):
    athlete = Athlete(email="equipment2@example.com")
    db_session.add(athlete)
    db_session.commit()

    profile = AthleteEquipmentProfile(athlete_id=athlete.id)
    db_session.add(profile)
    db_session.commit()

    fetched = db_session.get(AthleteEquipmentProfile, athlete.id)
    assert fetched.available_equipment == []


def test_one_profile_per_athlete_is_the_primary_key(db_session):
    athlete = Athlete(email="equipment3@example.com")
    db_session.add(athlete)
    db_session.commit()

    db_session.add(AthleteEquipmentProfile(athlete_id=athlete.id, available_equipment=["sled"]))
    db_session.commit()

    # Updating in place (not a second row) is the expected pattern — the PK is athlete_id itself.
    existing = db_session.get(AthleteEquipmentProfile, athlete.id)
    existing.available_equipment = ["sled", "rower"]
    db_session.commit()

    fetched = db_session.get(AthleteEquipmentProfile, athlete.id)
    assert fetched.available_equipment == ["sled", "rower"]
