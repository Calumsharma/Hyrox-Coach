"""Dialect-safe CHECK-constraint reassertion decision logic — Program Engine v5 Milestone 2,
migration 0005. Independent review, correction 2: the first fix checked existing constraint
NAMES, which is correct on SQLite but wrong on PostgreSQL, where 0004's two original
derivation-method constraints exist under a database-auto-generated name (0004 supplied no
explicit name), never the names this migration would look for. These tests exercise the decision
function directly with synthetic constraint metadata for both dialects — no live PostgreSQL
instance is needed or claimed to have been used.
"""

from app.services.capability_migration_support import (
    LOGGED_SESSION_CHECK_NAME,
    SELF_REPORT_CHECK_NAME,
    checks_to_create,
)

_SOURCE_CONSISTENCY = {"name": "ck_capability_assessment_source_consistency", "sqltext": "..."}


def test_sqlite_creates_both_when_neither_named_constraint_present():
    """The real first-upgrade case: SQLite has just recreated the table and silently dropped
    both unnamed originals."""
    existing = [_SOURCE_CONSISTENCY]
    result = checks_to_create("sqlite", existing)
    assert set(result) == {SELF_REPORT_CHECK_NAME, LOGGED_SESSION_CHECK_NAME}


def test_sqlite_creates_only_the_missing_one():
    existing = [_SOURCE_CONSISTENCY, {"name": SELF_REPORT_CHECK_NAME, "sqltext": "..."}]
    result = checks_to_create("sqlite", existing)
    assert result == [LOGGED_SESSION_CHECK_NAME]


def test_sqlite_creates_neither_when_both_already_named_and_present():
    """The re-upgrade-after-downgrade case: both named constraints already survived (downgrade
    no longer drops them), so re-running upgrade must not attempt to recreate either."""
    existing = [
        _SOURCE_CONSISTENCY,
        {"name": SELF_REPORT_CHECK_NAME, "sqltext": "..."},
        {"name": LOGGED_SESSION_CHECK_NAME, "sqltext": "..."},
    ]
    result = checks_to_create("sqlite", existing)
    assert result == []


def test_postgresql_never_creates_either_even_with_synthetic_autonamed_originals_present():
    """The exact bug this correction fixes: on PostgreSQL, 0004's two original constraints exist
    under the database's own auto-generated names (e.g. `capability_assessments_check1`) — never
    matching our chosen names. A name-only check would incorrectly conclude both are "missing"
    and add redundant duplicates. The dialect branch must return an empty list regardless of
    what's present, since PostgreSQL's native ALTER never put these at risk to begin with."""
    synthetic_postgres_constraints = [
        {"name": "capability_assessments_check1", "sqltext": "assessment_type <> 'self_report'::text OR derivation_method IS NULL"},
        {"name": "capability_assessments_check2", "sqltext": "assessment_type <> 'logged_session_derived'::text OR derivation_method IS NOT NULL"},
        {"name": "ck_capability_assessment_source_consistency", "sqltext": "..."},
    ]
    result = checks_to_create("postgresql", synthetic_postgres_constraints)
    assert result == []


def test_postgresql_never_creates_either_even_when_apparently_absent():
    """Same dialect branch, opposite input: even if a synthetic listing showed NEITHER expected
    name present, PostgreSQL still must not attempt creation — the absence of our name proves
    nothing on a dialect that never recreates the table."""
    result = checks_to_create("postgresql", [{"name": "ck_capability_assessment_source_consistency", "sqltext": "..."}])
    assert result == []


def test_unnamed_existing_constraints_are_ignored_not_mistaken_for_a_match():
    """A constraint dict with no `name` key (or `name=None`) must never be treated as satisfying
    either expected name."""
    existing = [{"name": None, "sqltext": "some other check"}, {"sqltext": "no name key at all"}]
    result = checks_to_create("sqlite", existing)
    assert set(result) == {SELF_REPORT_CHECK_NAME, LOGGED_SESSION_CHECK_NAME}
