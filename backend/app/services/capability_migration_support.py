"""Dialect-safe decision logic for migration 0005's conditional CHECK-constraint reassertion —
Program Engine v5 Milestone 2. Extracted into its own importable module (rather than living
inline in the migration file) so it can be unit-tested directly with synthetic constraint
metadata — Alembic version files have filenames starting with a digit, which are not valid
Python import targets, so testing this logic in place would require fragile dynamic-import
machinery instead of a plain `import`.
"""

from __future__ import annotations

SELF_REPORT_CHECK_NAME = "ck_capability_assessment_self_report_no_derivation_method"
LOGGED_SESSION_CHECK_NAME = "ck_capability_assessment_logged_session_has_derivation_method"


def checks_to_create(dialect_name: str, existing_check_constraints: list[dict]) -> list[str]:
    """Which of the two original 0004 derivation-method CHECK constraints (identified by the
    names above) migration 0005 still needs to (re)create, given the current dialect and the
    table's existing check constraints (in the shape `Inspector.get_check_constraints()` returns
    — a list of dicts with at least a `"name"` key).

    On SQLite, the table must be recreated (Alembic's batch mode) to add `ingested_at`'s NOT NULL
    constraint and the new `source_revision` CHECK — and that recreation, confirmed by directly
    inspecting the raw `sqlite_master.sql` after running it, silently DROPS any CHECK constraint
    that has no explicit name. 0004 created these two without one, so on SQLite they need
    reasserting, now named.

    On every other dialect — PostgreSQL, in practice — `ALTER TABLE` is native: none of 0005's
    other steps ever recreate the table, so 0004's two original constraints are never at risk
    there. They still exist, just under whatever name the database itself auto-assigned (never
    `SELF_REPORT_CHECK_NAME`/`LOGGED_SESSION_CHECK_NAME`, since 0004 supplied no explicit name at
    all). This deliberately does NOT try to match that auto-generated name by normalized SQL
    text — dialect identity alone determines whether recreation-related loss is even possible,
    so a non-SQLite dialect always returns an empty list here, regardless of what's already
    present, rather than risking a false-negative match on Postgres's own naming/formatting.
    """
    if dialect_name != "sqlite":
        return []

    existing_names = {c["name"] for c in existing_check_constraints if c.get("name")}
    to_create = []
    if SELF_REPORT_CHECK_NAME not in existing_names:
        to_create.append(SELF_REPORT_CHECK_NAME)
    if LOGGED_SESSION_CHECK_NAME not in existing_names:
        to_create.append(LOGGED_SESSION_CHECK_NAME)
    return to_create
