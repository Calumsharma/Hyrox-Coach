"""Two-path Alembic bootstrap, replacing the old implicit `Base.metadata.create_all(bind=engine)`.

See the Program Engine v5 plan, Milestone 1A, "Exact migration & rollback strategy" for the
full rationale. In short: a single baseline migration cannot both create a schema on an empty
database and act as a no-op against an already-populated one, so this module picks one of two
distinct paths at startup instead of trying to make one migration serve both:

- **Fresh database** (no tables at all): `alembic upgrade head` runs 0001_baseline for real,
  then 0002_v5_foundations on top — producing the complete schema in one pass.
- **Existing pre-Alembic database** (has tables, but no `alembic_version` — i.e. it predates
  this milestone): back it up, compare its schema against what 0001_baseline expects, fail
  safely on any drift, then `alembic stamp 0001_baseline` (recording that revision as applied
  WITHOUT executing its table-creation `upgrade()`) followed by `alembic upgrade head` — which,
  because 0001 is already stamped, executes only 0002_v5_foundations and later.

A database that already has an `alembic_version` table (already Alembic-managed, e.g. from a
prior run of this same bootstrap) skips both paths and just runs `alembic upgrade head`.

`Base.metadata.create_all` is never called from here — migrations are the only schema-changing
path, so they can never be silently bypassed.
"""

from __future__ import annotations

import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine

from app.config import settings

_ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"
_BASELINE_REVISION = "0001_baseline"


class SchemaDriftError(RuntimeError):
    """Raised when an existing pre-Alembic database's schema doesn't match what 0001_baseline
    expects. Refuses to proceed rather than guessing — see Milestone 1A's "fail safely" step."""


def _alembic_config() -> Config:
    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    return cfg


def _table_names(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def _schema_snapshot(engine: Engine) -> dict[str, list[tuple[str, str]]]:
    insp = inspect(engine)
    return {
        table: sorted((col["name"], str(col["type"])) for col in insp.get_columns(table))
        for table in insp.get_table_names()
        if table != "alembic_version"
    }


def _expected_baseline_schema() -> dict[str, list[tuple[str, str]]]:
    """The schema 0001_baseline produces, computed by actually running it against a throwaway
    on-disk database — rather than hand-duplicating column definitions here, which would be
    exactly the kind of drift-prone duplication this migration strategy is trying to avoid.
    (A real file is used, not `sqlite:///:memory:`, because Alembic's own engine and this
    function's inspection engine are separate connections — an in-memory database is invisible
    across separate connections, while a temp file is visible to both.)"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_db_path = Path(tmp_dir) / "reference_baseline.db"
        reference_cfg = Config(str(_ALEMBIC_INI))
        reference_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{tmp_db_path}")
        command.upgrade(reference_cfg, _BASELINE_REVISION)

        reference_engine = create_engine(f"sqlite:///{tmp_db_path}")
        try:
            return _schema_snapshot(reference_engine)
        finally:
            reference_engine.dispose()


def _backup_sqlite_file(database_url: str) -> Path | None:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix) or database_url.endswith(":memory:"):
        return None
    db_path = Path(database_url[len(prefix):])
    if not db_path.exists():
        return None
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = db_path.with_name(f"{db_path.name}.pre-alembic-backup-{timestamp}")
    shutil.copy2(db_path, backup_path)
    return backup_path


def ensure_schema_current() -> None:
    engine = create_engine(settings.database_url, connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {})
    try:
        existing_tables = _table_names(engine)
    finally:
        engine.dispose()

    cfg = _alembic_config()

    if "alembic_version" in existing_tables:
        # Already Alembic-managed (e.g. a prior run of this bootstrap) — just move to head.
        command.upgrade(cfg, "head")
        return

    if not existing_tables:
        # Fresh database — 0001_baseline creates the schema for real, then 0002 on top.
        command.upgrade(cfg, "head")
        return

    # Existing pre-Alembic database: back up, compare, fail safely, stamp, then upgrade.
    backup_path = _backup_sqlite_file(settings.database_url)
    if backup_path is None and settings.database_url.startswith("sqlite"):
        raise SchemaDriftError(
            "Refusing to bootstrap an existing pre-Alembic SQLite database whose file could not "
            "be located for backup. Resolve manually before restarting."
        )

    engine = create_engine(settings.database_url, connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {})
    try:
        actual_schema = _schema_snapshot(engine)
    finally:
        engine.dispose()
    expected_schema = _expected_baseline_schema()

    if actual_schema != expected_schema:
        missing_tables = set(expected_schema) - set(actual_schema)
        unexpected_tables = set(actual_schema) - set(expected_schema)
        column_mismatches = {
            table: (expected_schema.get(table), actual_schema.get(table))
            for table in set(expected_schema) | set(actual_schema)
            if table in expected_schema and table in actual_schema and expected_schema[table] != actual_schema[table]
        }
        raise SchemaDriftError(
            "Existing database schema does not match what 0001_baseline expects — refusing to "
            "proceed. A backup was taken at "
            f"{backup_path}. missing_tables={sorted(missing_tables)} "
            f"unexpected_tables={sorted(unexpected_tables)} column_mismatches={column_mismatches}"
        )

    command.stamp(cfg, _BASELINE_REVISION)
    command.upgrade(cfg, "head")
