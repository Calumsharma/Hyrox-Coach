"""Milestone 1A's load-bearing tests: the two-path Alembic bootstrap must never execute
0001_baseline's table-creation upgrade() against an existing populated database, must fail
safely on unexpected drift (across every aspect of the schema Inspector exposes, not just
columns), and 0002_v5_foundations/0003_1a_hardening must be genuinely reversible, additive-only
steps. See the Program Engine v5 plan, Milestone 1A, "Tests required", and the Milestone 1A
hardening pass that strengthened drift detection after an independent audit found the original
column-only comparison let a missing index through undetected."""

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


# --- Path 1: empty database -> upgrade to head ---

def test_empty_database_upgrade_to_head_matches_current_models(tmp_path):
    db_path = tmp_path / "fresh.db"
    db_url = f"sqlite:///{db_path}"
    command.upgrade(_alembic_config(db_url), "head")

    engine = create_engine(db_url)
    actual = db_bootstrap._schema_snapshot(engine)
    engine.dispose()

    reference_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=reference_engine)
    expected = db_bootstrap._schema_snapshot(reference_engine)
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


def _seed_representative_data(db_url: str) -> None:
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


def _assert_representative_data_unchanged(db_url: str) -> None:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT id, email FROM athletes")).fetchall() == [("athlete-1", "test@example.com")]
        assert conn.execute(text("SELECT id, athlete_id FROM training_blocks")).fetchall() == [("block-1", "athlete-1")]
        assert conn.execute(text("SELECT id, block_id, week_number FROM training_weeks")).fetchall() == [("week-1", "block-1", 1)]
        workout_row = conn.execute(text("SELECT id, week_id, logged_result, completed_at FROM workouts")).fetchall()
        assert workout_row == [("workout-1", "week-1", '{"rpe": 7}', "2026-09-01T08:00:00")]
    engine.dispose()


def test_legacy_database_stamp_and_upgrade_preserves_all_rows(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy.db"
    db_url = _build_legacy_database(db_path)
    _seed_representative_data(db_url)

    monkeypatch.setattr(db_bootstrap.settings, "database_url", db_url)
    monkeypatch.setattr(db_bootstrap, "_ALEMBIC_INI", ALEMBIC_INI)

    db_bootstrap.ensure_schema_current()

    _assert_representative_data_unchanged(db_url)

    engine = create_engine(db_url)
    with engine.connect() as conn:
        # Ruleset data migration ran too, since it's part of 0002_v5_foundations.
        rule_sets = conn.execute(text("SELECT id FROM race_rule_sets")).fetchall()
        assert rule_sets == [("hyrox_singles_2026_27",)]

        # Confirms the full chain (0001 stamped, 0002/0003/0004 executed) actually ran, not
        # just 0002 — every later migration's constraints must be present on a fresh legacy
        # upgrade too, including 0004's additive unique constraints on these two pre-existing
        # tables.
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        assert version == "0004_capability_foundation"
        unique_constraints = inspect(engine).get_unique_constraints("scheduling_constraints")
        assert {"athlete_id", "day_of_week"} == set(unique_constraints[0]["column_names"])
        assert any(
            set(uc["column_names"]) == {"id", "athlete_id"}
            for uc in inspect(engine).get_unique_constraints("recovery_readings")
        )
        assert any(
            set(uc["column_names"]) == {"id", "athlete_id"}
            for uc in inspect(engine).get_unique_constraints("past_hyrox_results")
        )
    engine.dispose()


def _run_drift_test(tmp_path, monkeypatch, mutate) -> None:
    """Shared body for every drift test: build a legacy DB with representative data, apply
    `mutate` to damage it, run the real bootstrap, and assert it refuses safely."""
    db_path = tmp_path / "drifted.db"
    db_url = _build_legacy_database(db_path)
    _seed_representative_data(db_url)
    mutate(db_url)

    monkeypatch.setattr(db_bootstrap.settings, "database_url", db_url)
    monkeypatch.setattr(db_bootstrap, "_ALEMBIC_INI", ALEMBIC_INI)

    with pytest.raises(db_bootstrap.SchemaDriftError):
        db_bootstrap.ensure_schema_current()

    engine = create_engine(db_url)
    tables = set(inspect(engine).get_table_names())
    engine.dispose()
    assert "alembic_version" not in tables
    assert not ({"race_rule_sets", "programme_decisions", "athlete_equipment_profiles", "scheduling_constraints"} & tables)
    _assert_representative_data_unchanged(db_url)


def test_legacy_database_missing_column_fails_safely(tmp_path, monkeypatch):
    def mutate(db_url):
        engine = create_engine(db_url)
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE athletes DROP COLUMN height_cm"))
        engine.dispose()

    _run_drift_test(tmp_path, monkeypatch, mutate)


def test_legacy_database_missing_index_fails_safely(tmp_path, monkeypatch):
    """Independently reproduced audit finding: the original drift check compared only
    (column_name, column_type) and did not notice a dropped index at all — it incorrectly
    stamped and upgraded a database missing ix_training_blocks_athlete_id. The strengthened
    `_schema_snapshot` compares indexes explicitly, so this must now be refused."""
    def mutate(db_url):
        engine = create_engine(db_url)
        with engine.begin() as conn:
            conn.execute(text("DROP INDEX ix_training_blocks_athlete_id"))
        engine.dispose()

    _run_drift_test(tmp_path, monkeypatch, mutate)


def test_legacy_database_lost_unique_constraint_fails_safely(tmp_path, monkeypatch):
    """A changed column property / missing constraint: athletes.email is expected to be
    uniquely indexed. Recreating it as a plain (non-unique) index must be caught."""
    def mutate(db_url):
        engine = create_engine(db_url)
        with engine.begin() as conn:
            conn.execute(text("DROP INDEX ix_athletes_email"))
            conn.execute(text("CREATE INDEX ix_athletes_email ON athletes (email)"))
        engine.dispose()

    _run_drift_test(tmp_path, monkeypatch, mutate)


# --- Downgrade/re-upgrade of 0003 only, on an ephemeral test database ---
# `downgrade base` (dropping the pre-v5 schema entirely) is exercised here too, but ONLY against
# this kind of fully disposable database — never treated as a real-data rollback strategy.

def test_downgrade_and_reupgrade_0003_is_idempotent(tmp_path):
    db_path = tmp_path / "roundtrip.db"
    db_url = f"sqlite:///{db_path}"
    cfg = _alembic_config(db_url)

    command.upgrade(cfg, "0002_v5_foundations")
    command.upgrade(cfg, "0003_1a_hardening")
    engine = create_engine(db_url)
    schema_first = db_bootstrap._schema_snapshot(engine)
    engine.dispose()

    command.downgrade(cfg, "0002_v5_foundations")
    command.upgrade(cfg, "0003_1a_hardening")
    engine = create_engine(db_url)
    schema_second = db_bootstrap._schema_snapshot(engine)
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


# --- Downgrade/re-upgrade of 0004 only, on an ephemeral test database ---

def test_downgrade_and_reupgrade_0004_is_idempotent(tmp_path):
    db_path = tmp_path / "roundtrip_0004.db"
    db_url = f"sqlite:///{db_path}"
    cfg = _alembic_config(db_url)

    command.upgrade(cfg, "0003_1a_hardening")
    command.upgrade(cfg, "0004_capability_foundation")
    engine = create_engine(db_url)
    schema_first = db_bootstrap._schema_snapshot(engine)
    engine.dispose()

    command.downgrade(cfg, "0003_1a_hardening")
    command.upgrade(cfg, "0004_capability_foundation")
    engine = create_engine(db_url)
    schema_second = db_bootstrap._schema_snapshot(engine)
    engine.dispose()

    assert schema_first == schema_second


# --- 0003_1a_hardening's own fail-safe pre-check: refuses to add constraints over violating data ---

def test_0003_refuses_to_add_unique_constraint_over_existing_duplicates(tmp_path):
    db_path = tmp_path / "dupe.db"
    db_url = f"sqlite:///{db_path}"
    cfg = _alembic_config(db_url)
    command.upgrade(cfg, "0002_v5_foundations")

    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO athletes (id, email, onboarding_completed, self_reported_weak_stations, created_at) "
            "VALUES ('a1', 'dupe@example.com', 0, '[]', '2026-09-01T00:00:00')"
        ))
        conn.execute(text(
            "INSERT INTO scheduling_constraints (id, athlete_id, day_of_week, available, notes) "
            "VALUES ('s1', 'a1', 1, 1, '')"
        ))
        conn.execute(text(
            "INSERT INTO scheduling_constraints (id, athlete_id, day_of_week, available, notes) "
            "VALUES ('s2', 'a1', 1, 1, 'dup')"
        ))
    engine.dispose()

    with pytest.raises(RuntimeError, match="duplicate"):
        command.upgrade(cfg, "0003_1a_hardening")

    engine = create_engine(db_url)
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        assert version == "0002_v5_foundations"
        rows = conn.execute(text("SELECT id FROM scheduling_constraints ORDER BY id")).fetchall()
        assert rows == [("s1",), ("s2",)]
    engine.dispose()
