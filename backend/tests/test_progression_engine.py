from datetime import date

from app.models import Athlete, TrainingBlock, TrainingWeek, Workout
from app.schemas.training import BlockLog, ConditioningLog, SetLog, WorkoutLogUpdate
from app.services.progression_engine import apply_progression


def _make_two_week_block(db_session, week1_prescription, week2_prescription, day_of_week=0):
    athlete = Athlete(email="progression-test@example.com")
    db_session.add(athlete)
    db_session.flush()

    block = TrainingBlock(athlete_id=athlete.id, start_date=date(2026, 1, 1), length_weeks=2)
    db_session.add(block)
    db_session.flush()

    week1 = TrainingWeek(block_id=block.id, week_number=1, phase="base")
    week2 = TrainingWeek(block_id=block.id, week_number=2, phase="build")
    db_session.add_all([week1, week2])
    db_session.flush()

    workout1 = Workout(week_id=week1.id, day_of_week=day_of_week, workout_type="strength", title="Forge", prescription=week1_prescription)
    workout2 = Workout(week_id=week2.id, day_of_week=day_of_week, workout_type="strength", title="Forge", prescription=week2_prescription)
    db_session.add_all([workout1, workout2])
    db_session.commit()
    db_session.refresh(workout1)
    return workout1, workout2


def test_low_rpe_increases_suggested_load(db_session):
    prescription = {"blocks": [{"movement": "barbell_front_squat", "sets": 4, "reps": 5}]}
    workout1, workout2 = _make_two_week_block(db_session, prescription, prescription)

    payload = WorkoutLogUpdate(blocks=[BlockLog(index=0, sets=[SetLog(reps=5, weight_kg=100)], rpe=6)])
    apply_progression(db_session, workout1, payload)

    db_session.refresh(workout2)
    target_block = workout2.prescription["blocks"][0]
    assert target_block["suggested_load_kg"] == round(100 * 1.025, 1)
    assert "room" in target_block["progression_note"]


def test_high_rpe_holds_load_flat(db_session):
    prescription = {"blocks": [{"movement": "hex_bar_deadlift", "sets": 4, "reps": 5}]}
    workout1, workout2 = _make_two_week_block(db_session, prescription, prescription)

    payload = WorkoutLogUpdate(blocks=[BlockLog(index=0, sets=[SetLog(reps=5, weight_kg=140)], rpe=9.5)])
    apply_progression(db_session, workout1, payload)

    db_session.refresh(workout2)
    target_block = workout2.prescription["blocks"][0]
    assert target_block["suggested_load_kg"] == 140
    assert "near max" in target_block["progression_note"]


def test_no_future_occurrence_of_movement_is_a_graceful_no_op(db_session):
    week1_prescription = {"blocks": [{"movement": "barbell_front_squat", "sets": 4, "reps": 5}]}
    week2_prescription = {"blocks": [{"movement": "hex_bar_deadlift", "sets": 4, "reps": 5}]}  # different movement
    workout1, workout2 = _make_two_week_block(db_session, week1_prescription, week2_prescription)

    payload = WorkoutLogUpdate(blocks=[BlockLog(index=0, sets=[SetLog(reps=5, weight_kg=100)], rpe=6)])
    apply_progression(db_session, workout1, payload)  # should not raise

    db_session.refresh(workout2)
    assert "suggested_load_kg" not in workout2.prescription["blocks"][0]


def test_last_week_of_block_has_nothing_to_annotate(db_session):
    prescription = {"blocks": [{"movement": "barbell_front_squat", "sets": 4, "reps": 5}]}
    workout1, workout2 = _make_two_week_block(db_session, prescription, prescription)

    payload = WorkoutLogUpdate(blocks=[BlockLog(index=0, sets=[SetLog(reps=5, weight_kg=100)], rpe=6)])
    apply_progression(db_session, workout2, payload)  # logging the LAST week — no future week exists

    db_session.refresh(workout2)
    assert "suggested_load_kg" not in workout2.prescription["blocks"][0]


def test_conditioning_comparison_populates_on_next_matching_format(db_session):
    prescription = {"conditioning": {"format": "amrap", "duration_min": 15, "movements": ["20 wall balls"]}}
    workout1, workout2 = _make_two_week_block(db_session, prescription, prescription)

    payload = WorkoutLogUpdate(conditioning=ConditioningLog(rounds_completed=4, extra_reps=10, rpe=9))
    apply_progression(db_session, workout1, payload)

    db_session.refresh(workout2)
    conditioning = workout2.prescription["conditioning"]
    assert conditioning["previous_rounds_completed"] == 4
    assert conditioning["previous_extra_reps"] == 10
    assert conditioning["previous_rpe"] == 9
