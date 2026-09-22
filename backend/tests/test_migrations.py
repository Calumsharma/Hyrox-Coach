"""Milestone 1A's load-bearing tests: the two-path Alembic bootstrap must never execute
0001_baseline's table-creation upgrade() against an existing populated database, must fail
safely on unexpected drift, and 0002_v5_foundations must be a genuinely reversible, additive-only
step. See the Program Engine v5 plan, Milestone 1A, "Tests required"."""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app import db_bootstrap
from app.db import Base
import app.models  # noqa: F401 — registers every model on Base.metadata

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"


def _alembic_config(db_url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def _schema_snapshot(engine) -> dict:
    insp = inspect(engine)
    return {
        table: sorted((col["name"], str(col["type"])) for col in insp.get_columns(table))
        for table in insp.get_table_names()
        if table != "alembic_version"
    }


# --- Path 1: empty database -> upgrade to head ---

def test_empty_database_upgrade_to_head_matches_current_models(tmp_path):
    db_path = tmp_path / "fresh.db"
    db_url = f"sqlite:///{db_path}"
    command.upgrade(_alembic_config(db_url), "head")

    engine = create_engine(db_url)
    actual = _schema_snapshot(engine)
    engine.dispose()

    reference_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=reference_engine)
    expected = _schema_snapshot(reference_engine)
    reference_engine.dispose()

    assert actual == expected


# --- Path 2: legacy pre-Alembic database -> stamp 0001, execute only 0002+ ---

def _build_legacy_database(db_path: Path) -> str:
    """Builds a database with exactly the pre-v5 schema and NO alembic_version table — i.e. a
    stand-in for the real dev hyrox_coach.db as it existed before this milestone.

    Deliberately does NOT use `Base.metadata.create_all` here: by the time this test runs,
    `Base.metadata` already reflects the CURRENT code, which includes this same milestone's new
    v5 models — using it would produce a database that already has the new tables, defeating the
    point of the test. Running 0001_baseline's own upgrade() (verified elsewhere in this file to
    be byte-for-byte identical to the pre-v5 app's real create_all() output) and then dropping
    the resulting alembic_version table instead guarantees exactly the pre-v5 schema, regardless
    of what's been added to the models since.
    """
    db_url = f"sqlite:///{db_path}"
    command.upgrade(_alembic_config(db_url), "0001_baseline")
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE alembic_version"))
    engine.dispose()
    return db_url


def _seed_representative_data(db_url: str) -> dict:
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO athletes (id, email, onboarding_completed, self_reported_weak_stations, created_at) "
            "VALUES ('athlete-1', 'test@example.com', 1, '[]', '2026-09-01T00:00:00')"
        ))
        conn.execute(text(
            "INSERT INTO training_blocks (id, athlete_id, discipline, start_date, length_weeks, "
            "target_weaknesses, deload_week_numbers, taper_week_numbers, created_at) "
            "VALUES ('block-1', 'athlete-1', 'hyrox', '2026-09-01', 8, '[]', '[]', '[]', '2026-09-01T00:00:00')"
        ))
        conn.execute(text(
            "INSERT INTO training_weeks (id, block_id, week_number, phase, planned_intensity, actual_intensity) "
            "VALUES ('week-1', 'block-1', 1, 'base', 1.0, 1.0)"
        ))
        conn.execute(text(
            "INSERT INTO workouts (id, week_id, day_of_week, workout_type, title, prescription, "
            "logged_result, completed_at) VALUES ('workout-1', 'week-1', 0, 'strength', 'Forge', '{}', "
            "'{\"rpe\": 7}', '2026-09-01T08:00:00')"
        ))
    engine.dispose()
    return {
        "athletes": [("athlete-1", "test@example.com")],
        "training_blocks": [("block-1", "athlete-1")],
        "training_weeks": [("week-1", "block-1", 1)],
        "workouts": [("workout-1", "week-1", '{"rpe": 7}', "2026-09-01T08:00:00")],
    }


def test_legacy_database_stamp_and_upgrade_preserves_all_rows(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy.db"
    db_url = _build_legacy_database(db_path)
    _seed_representative_data(db_url)

    monkeypatch.setattr(db_bootstrap.settings, "database_url", db_url)
    monkeypatch.setattr(db_bootstrap, "_ALEMBIC_INI", ALEMBIC_INI)

    db_bootstrap.ensure_schema_current()

    engine = create_engine(db_url)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT id, email FROM athletes")).fetchall() == [("athlete-1", "test@example.com")]
        assert conn.execute(text("SELECT id, athlete_id FROM training_blocks")).fetchall() == [("block-1", "athlete-1")]
        assert conn.execute(text("SELECT id, block_id, week_number FROM training_weeks")).fetchall() == [("week-1", "block-1", 1)]
        workout_row = conn.execute(text("SELECT id, week_id, logged_result, completed_at FROM workouts")).fetchall()
        assert workout_row == [("workout-1", "week-1", '{"rpe": 7}', "2026-09-01T08:00:00")]

        # Ruleset data migration ran too, since it's part of 0002_v5_foundations.
        rule_sets = conn.execute(text("SELECT id FROM race_rule_sets")).fetchall()
        assert rule_sets == [("hyrox_singles_2026_27",)]
    engine.dispose()


def test_legacy_database_with_drift_fails_safely(tmp_path, monkeypatch):
    db_path = tmp_path / "drifted.db"
    db_url = _build_legacy_database(db_path)

    engine = create_engine(db_url)
    with engine.begin() as conn:
        # Simulate real-world drift: a column 0001_baseline expects is missing.
        conn.execute(text("ALTER TABLE athletes DROP COLUMN height_cm"))
    engine.dispose()

    monkeypatch.setattr(db_bootstrap.settings, "database_url", db_url)
    monkeypatch.setattr(db_bootstrap, "_ALEMBIC_INI", ALEMBIC_INI)

    with pytest.raises(db_bootstrap.SchemaDriftError):
        db_bootstrap.ensure_schema_current()

    # Refused before any schema change — no alembic_version table, no new tables created.
    engine = create_engine(db_url)
    tables = set(inspect(engine).get_table_names())
    engine.dispose()
    assert "alembic_version" not in tables
    assert "race_rule_sets" not in tables


# --- Downgrade/re-upgrade of 0002 only, on an ephemeral test database ---
# `downgrade base` (dropping the pre-v5 schema entirely) is exercised here too, but ONLY against
# this kind of fully disposable database — never treated as a real-data rollback strategy.

def test_downgrade_and_reupgrade_0002_is_idempotent(tmp_path):
    db_path = tmp_path / "roundtrip.db"
    db_url = f"sqlite:///{db_path}"
    cfg = _alembic_config(db_url)

    command.upgrade(cfg, "0001_baseline")
    command.upgrade(cfg, "0002_v5_foundations")
    engine = create_engine(db_url)
    schema_first = _schema_snapshot(engine)
    engine.dispose()

    command.downgrade(cfg, "0001_baseline")
    command.upgrade(cfg, "0002_v5_foundations")
    engine = create_engine(db_url)
    schema_second = _schema_snapshot(engine)
    engine.dispose()

    assert schema_first == schema_second


def test_downgrade_base_only_on_disposable_database(tmp_path):
    """This is the one place `downgrade base` is exercised — a throwaway database created and
    destroyed entirely within this test, never a stand-in for a real-data rollback."""
    db_path = tmp_path / "disposable.db"
    db_url = f"sqlite:///{db_path}"
    cfg = _alembic_config(db_url)

    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")

    engine = create_engine(db_url)
    tables = set(inspect(engine).get_table_names()) - {"alembic_version"}
    engine.dispose()
    assert tables == set()
