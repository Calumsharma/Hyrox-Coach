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


# --- Canonical, deterministic per-table schema signature ---
#
# The original snapshot compared only (column_name, column_type) per table. An independent
# audit found this insufficient to back this module's own claim of "schema equivalence" — it
# would, for example, silently accept a database missing an expected index. This version
# compares columns (name/type/nullable/default), primary key, indexes, unique constraints,
# foreign keys, and check constraints — everything SQLAlchemy's Inspector exposes that a
# migration can meaningfully change. Every part is normalized (sorted, whitespace/case-folded)
# so two structurally-equivalent SQLite schemas compare equal regardless of reflection ordering
# or minor dialect text formatting.

def _normalize_type(col_type) -> str:
    return "".join(str(col_type).split()).upper()


def _normalize_default(default) -> str | None:
    if default is None:
        return None
    return "".join(str(default).split()).upper()


def _column_signature(col: dict) -> tuple:
    return (
        col["name"],
        _normalize_type(col["type"]),
        bool(col["nullable"]),
        _normalize_default(col.get("default")),
    )


def _index_signature(idx: dict) -> tuple:
    return (tuple(sorted(idx["column_names"])), bool(idx["unique"]))


def _unique_constraint_signature(uc: dict) -> tuple:
    return tuple(sorted(uc["column_names"]))


def _foreign_key_signature(fk: dict) -> tuple:
    return (
        tuple(sorted(fk["constrained_columns"])),
        fk["referred_table"],
        tuple(sorted(fk["referred_columns"])),
    )


def _check_constraint_signature(ck: dict) -> str:
    # SQLite reflects check constraints by parsing the CREATE TABLE text back out, so trivial
    # whitespace/quoting differences are possible between two structurally-identical
    # constraints. Case- and whitespace-normalizing catches that without masking a real
    # difference in the actual condition.
    return "".join((ck.get("sqltext") or "").split()).lower()


def _table_signature(insp, table: str) -> dict:
    pk = insp.get_pk_constraint(table) or {}
    return {
        "columns": sorted(_column_signature(c) for c in insp.get_columns(table)),
        "primary_key": tuple(sorted(pk.get("constrained_columns") or [])),
        "indexes": sorted(_index_signature(i) for i in insp.get_indexes(table)),
        "unique_constraints": sorted(_unique_constraint_signature(u) for u in insp.get_unique_constraints(table)),
        "foreign_keys": sorted(_foreign_key_signature(f) for f in insp.get_foreign_keys(table)),
        "check_constraints": sorted(_check_constraint_signature(c) for c in insp.get_check_constraints(table)),
    }


def _schema_snapshot(engine: Engine) -> dict[str, dict]:
    insp = inspect(engine)
    return {
        table: _table_signature(insp, table)
        for table in insp.get_table_names()
        if table != "alembic_version"
    }


def _describe_schema_drift(expected: dict[str, dict], actual: dict[str, dict]) -> str:
    """Human-readable diff of a schema mismatch, for the SchemaDriftError message."""
    missing_tables = sorted(set(expected) - set(actual))
    unexpected_tables = sorted(set(actual) - set(expected))
    parts = []
    if missing_tables:
        parts.append(f"missing_tables={missing_tables}")
    if unexpected_tables:
        parts.append(f"unexpected_tables={unexpected_tables}")
    for table in sorted(set(expected) & set(actual)):
        if expected[table] == actual[table]:
            continue
        table_diffs = []
        for aspect in ("columns", "primary_key", "indexes", "unique_constraints", "foreign_keys", "check_constraints"):
            if expected[table][aspect] != actual[table][aspect]:
                table_diffs.append(f"{aspect}: expected={expected[table][aspect]!r} actual={actual[table][aspect]!r}")
        parts.append(f"table '{table}' differs — " + "; ".join(table_diffs))
    return " | ".join(parts)


def _expected_baseline_schema() -> dict[str, dict]:
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
        raise SchemaDriftError(
            "Existing database schema does not match what 0001_baseline expects — refusing to "
            f"proceed. A backup was taken at {backup_path}. "
            f"{_describe_schema_drift(expected_schema, actual_schema)}"
        )

    command.stamp(cfg, _BASELINE_REVISION)
    command.upgrade(cfg, "head")
