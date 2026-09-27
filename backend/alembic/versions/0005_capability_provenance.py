"""capability provenance — Program Engine v5 Milestone 2.

Eight-step safe sequence (see the Milestone 2 v2.2 plan, §J):

1. Add RecoveryReading.vo2_max_source/vo2_max_recorded_at/vo2_max_updated_at as nullable
   columns — no default, no backfill, correctly NULL on every pre-existing row (unknown, never
   guessed).
2. Add CapabilityAssessment.ingested_at as nullable (NOT NULL comes only after backfill).
3. Backfill ingested_at = recorded_at for any representative row that happens to exist.
4. Enforce NOT NULL on ingested_at, now that every row has a value.
5. Add CapabilityAssessment.source_revision as nullable — no CHECK yet.
6. Defensively backfill any pre-existing wearable_derived row with a null source_revision to
   the 'unknown_historical' sentinel. No real database has such a row today (Milestone 2 is
   what first writes to capability_assessments at all), but this migration does not assume
   that — it never guesses a provider, value, or timestamp, only ever writes this one sentinel.
7. Add the CHECK (assessment_type != 'wearable_derived' OR source_revision IS NOT NULL) — safe
   to add unconditionally now that step 6 guarantees no existing row can violate it.
8. No temporary default was introduced at any step, so there is nothing to remove.

Purely additive throughout — downgrade() reverses steps 7 -> 1.

Real bug found and fixed while writing this migration: Alembic's SQLite batch-mode table
recreation (required for steps 4 and 7, since SQLite has no native ALTER COLUMN / ADD
CONSTRAINT) silently DROPS unnamed CHECK constraints during reflection-based recreation —
confirmed by inspecting the raw `sqlite_master.sql` after upgrading, which was missing both of
0004's original unnamed `derivation_method` CHECK constraints entirely. Since `0004_capability_
foundation.py` itself must never be edited, those two constraints are explicitly RE-ASSERTED
here, now named (`app/models/capability.py` is updated to match).

**Corrected per independent review**: `downgrade()` no longer drops these two named constraints.
A database downgraded to `0004` keeps both derivation-method integrity rules enforced throughout
— named rather than anonymous, but functionally identical, and never absent even transiently.

**Second correction, same review round**: `upgrade()`'s reassertion step is now genuinely
dialect-safe, not just conditional-by-name. The first version of this fix checked existing check
constraint NAMES before recreating — correct on SQLite, but wrong on PostgreSQL: 0004 created
these two constraints with no explicit `name=`, so on PostgreSQL the database itself auto-assigns
a name (never `ck_capability_assessment_self_report_no_derivation_method`/
`ck_capability_assessment_logged_session_has_derivation_method`), and PostgreSQL's `ALTER TABLE`
is native — none of this migration's earlier steps ever recreate the table there, so those two
constraints are never at risk of being dropped on that dialect in the first place. A name-only
check would therefore never find them under our chosen names and would add a second, redundant,
differently-named constraint enforcing the same rule. The fix (`app/services/
capability_migration_support.py::checks_to_create`, unit-tested with synthetic Postgres-style
auto-named constraint metadata) branches on dialect identity instead of trying to match an
auto-generated name by normalized SQL text: on SQLite it reasserts whichever of the two named
constraints isn't already present; on every other dialect it reasserts neither, since native
ALTER means they were never lost. No live PostgreSQL instance is available in this environment —
this is verified by reasoning about Postgres's native ALTER semantics, a dedicated unit test of
the decision function against synthetic Postgres-shaped metadata, and the SQLite round-trip
tests — never claimed as having been run against a real PostgreSQL database.

Revision ID: 0005_capability_provenance
Revises: 0004_capability_foundation
Create Date: 2026-09-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.services.capability_migration_support import (
    LOGGED_SESSION_CHECK_NAME as _LOGGED_SESSION_CHECK_NAME,
    SELF_REPORT_CHECK_NAME as _SELF_REPORT_CHECK_NAME,
    checks_to_create,
)


# revision identifiers, used by Alembic.
revision: str = '0005_capability_provenance'
down_revision: Union[str, Sequence[str], None] = '0004_capability_foundation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_WEARABLE_DERIVED_CHECK_NAME = 'ck_capability_assessment_wearable_derived_has_source_revision'


def upgrade() -> None:
    """Upgrade schema — eight ordered steps, see module docstring."""
    conn = op.get_bind()

    # 1. RecoveryReading VO2max field-level provenance — nullable, no backfill.
    with op.batch_alter_table('recovery_readings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('vo2_max_source', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('vo2_max_recorded_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('vo2_max_updated_at', sa.DateTime(), nullable=True))

    # 2. CapabilityAssessment.ingested_at — nullable first, NOT NULL only after backfill (step 4).
    with op.batch_alter_table('capability_assessments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ingested_at', sa.DateTime(), nullable=True))

    # 3. Backfill ingested_at from recorded_at for any representative row that happens to exist.
    conn.execute(sa.text("UPDATE capability_assessments SET ingested_at = recorded_at WHERE ingested_at IS NULL"))

    # 4. Enforce NOT NULL now that every row has a value.
    with op.batch_alter_table('capability_assessments', schema=None) as batch_op:
        batch_op.alter_column('ingested_at', existing_type=sa.DateTime(), nullable=False)

    # 5. CapabilityAssessment.source_revision — nullable, no CHECK yet.
    with op.batch_alter_table('capability_assessments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source_revision', sa.String(), nullable=True))

    # 6. Defensive backfill — see module docstring. Affects zero rows in any real database today.
    conn.execute(sa.text(
        "UPDATE capability_assessments SET source_revision = 'unknown_historical' "
        "WHERE assessment_type = 'wearable_derived' AND source_revision IS NULL"
    ))

    # 7. Now safe to add the wearable_derived CHECK unconditionally (it's new in 0005, so it can
    #    never already exist on any dialect). Re-assertion of the two original 0004 CHECK
    #    constraints is dialect-safe (see module docstring / `checks_to_create`'s own docstring):
    #    SQLite recreates the table for this step and silently drops unnamed constraints, so it
    #    reasserts whichever named one isn't already present; every other dialect (PostgreSQL, in
    #    practice) never recreates the table here, so nothing is reasserted there — those two
    #    constraints already exist, just under a database-assigned name we deliberately don't try
    #    to match.
    dialect_name = conn.dialect.name
    existing_check_constraints = sa.inspect(conn).get_check_constraints('capability_assessments')
    names_to_create = checks_to_create(dialect_name, existing_check_constraints)
    check_conditions = {
        _SELF_REPORT_CHECK_NAME: "assessment_type != 'self_report' OR derivation_method IS NULL",
        _LOGGED_SESSION_CHECK_NAME: "assessment_type != 'logged_session_derived' OR derivation_method IS NOT NULL",
    }

    with op.batch_alter_table('capability_assessments', schema=None) as batch_op:
        batch_op.create_check_constraint(
            _WEARABLE_DERIVED_CHECK_NAME,
            "assessment_type != 'wearable_derived' OR source_revision IS NOT NULL",
        )
        for name in names_to_create:
            batch_op.create_check_constraint(name, check_conditions[name])

    # 8. No temporary default was introduced at any step, so there is nothing to remove.


def downgrade() -> None:
    """Downgrade schema — reverses steps 7 -> 1. **Corrected per independent review**: the two
    original derivation-method CHECK constraints (`_SELF_REPORT_CHECK_NAME`,
    `_LOGGED_SESSION_CHECK_NAME`) are deliberately NOT dropped here — they are 0004's own
    integrity rules, now named only because of the SQLite batch-recreation bug documented above,
    and downgrading to 0004 must not remove enforcement that milestone shipped. Only the
    genuinely new-in-0005 `_WEARABLE_DERIVED_CHECK_NAME` constraint and the new columns are
    reversed. Because these two constraints are named, they survive every subsequent batch
    recreation below automatically (the same reflection mechanism that silently drops UNNAMED
    constraints correctly preserves NAMED ones) — no extra action is needed to keep them."""
    with op.batch_alter_table('capability_assessments', schema=None) as batch_op:
        batch_op.drop_constraint(_WEARABLE_DERIVED_CHECK_NAME, type_='check')
        batch_op.drop_column('source_revision')
    with op.batch_alter_table('capability_assessments', schema=None) as batch_op:
        batch_op.alter_column('ingested_at', existing_type=sa.DateTime(), nullable=True)
    with op.batch_alter_table('capability_assessments', schema=None) as batch_op:
        batch_op.drop_column('ingested_at')

    with op.batch_alter_table('recovery_readings', schema=None) as batch_op:
        batch_op.drop_column('vo2_max_updated_at')
        batch_op.drop_column('vo2_max_recorded_at')
        batch_op.drop_column('vo2_max_source')
