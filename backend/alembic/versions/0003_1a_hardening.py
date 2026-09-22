"""1A hardening — validated SchedulingConstraint constraints.

Independent audit of Milestone 1A found that `scheduling_constraints` had no protection against
duplicate (athlete_id, day_of_week) rows, out-of-range `day_of_week` values, or non-positive
`max_duration_minutes`. This migration adds a unique constraint and two check constraints for
those — but first inspects the EXISTING data and refuses to proceed if any row already violates
one of them. It never silently deletes, merges, or rewrites data; a violation found here is a
data problem for a human to resolve, not something this migration decides how to fix.

(ProgrammeDecision's append-only enforcement, the other half of this hardening pass, is pure
application-level SQLAlchemy mapper-event code — see app/models/programme_decision.py — and
needs no schema change, so it isn't part of this migration.)

This is a NEW migration on top of the already-deployed 0001_baseline/0002_v5_foundations — those
two files are not rewritten or amended, since the real dev database has already reached 0002.

Revision ID: 0003_1a_hardening
Revises: 0002_v5_foundations
Create Date: 2026-09-22 17:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003_1a_hardening'
down_revision: Union[str, Sequence[str], None] = '0002_v5_foundations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_UNIQUE_NAME = 'uq_scheduling_constraint_athlete_day'
_DAY_RANGE_CHECK_NAME = 'ck_scheduling_constraint_day_of_week_range'
_DURATION_CHECK_NAME = 'ck_scheduling_constraint_max_duration_positive'


def upgrade() -> None:
    conn = op.get_bind()

    duplicates = conn.execute(sa.text(
        "SELECT athlete_id, day_of_week, COUNT(*) AS n FROM scheduling_constraints "
        "GROUP BY athlete_id, day_of_week HAVING COUNT(*) > 1"
    )).fetchall()
    if duplicates:
        raise RuntimeError(
            "0003_1a_hardening: refusing to add a unique constraint on "
            "scheduling_constraints(athlete_id, day_of_week) — existing duplicate rows found: "
            f"{[tuple(row) for row in duplicates]}. Resolve these rows manually, then re-run "
            "this migration."
        )

    bad_days = conn.execute(sa.text(
        "SELECT id, day_of_week FROM scheduling_constraints WHERE day_of_week < 0 OR day_of_week > 6"
    )).fetchall()
    if bad_days:
        raise RuntimeError(
            "0003_1a_hardening: refusing to add the day_of_week range check — existing rows "
            f"outside 0-6 found: {[tuple(row) for row in bad_days]}. Resolve these rows "
            "manually, then re-run this migration."
        )

    bad_durations = conn.execute(sa.text(
        "SELECT id, max_duration_minutes FROM scheduling_constraints "
        "WHERE max_duration_minutes IS NOT NULL AND max_duration_minutes <= 0"
    )).fetchall()
    if bad_durations:
        raise RuntimeError(
            "0003_1a_hardening: refusing to add the max_duration_minutes positivity check — "
            f"existing non-positive values found: {[tuple(row) for row in bad_durations]}. "
            "Resolve these rows manually, then re-run this migration."
        )

    with op.batch_alter_table('scheduling_constraints', schema=None) as batch_op:
        batch_op.create_unique_constraint(_UNIQUE_NAME, ['athlete_id', 'day_of_week'])
        batch_op.create_check_constraint(_DAY_RANGE_CHECK_NAME, 'day_of_week BETWEEN 0 AND 6')
        batch_op.create_check_constraint(_DURATION_CHECK_NAME, 'max_duration_minutes IS NULL OR max_duration_minutes > 0')


def downgrade() -> None:
    with op.batch_alter_table('scheduling_constraints', schema=None) as batch_op:
        batch_op.drop_constraint(_DURATION_CHECK_NAME, type_='check')
        batch_op.drop_constraint(_DAY_RANGE_CHECK_NAME, type_='check')
        batch_op.drop_constraint(_UNIQUE_NAME, type_='unique')
