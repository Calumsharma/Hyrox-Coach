"""v5 foundations — additive-only structural tables + the RaceRuleSet ruleset data migration.

Adds `rule_set_version` to `station_reference` and the `race_rule_sets`, `programme_decisions`,
`athlete_equipment_profiles`, `scheduling_constraints` tables — the four structural tables
Milestone 1A needs that depend on zero unresolved coaching decision (Program Engine v5 plan,
§8). Also performs the ruleset data migration: inserts the one real RaceRuleSet row, backfills
every existing StationReference row's rule_set_version, and verifies none is left unversioned.

`downgrade()` drops exactly what `upgrade()` created — purely additive, so the round trip is
schema-identical. SQLite can't ALTER a constraint outside batch mode, so the new column/FK on
`station_reference` use `op.batch_alter_table`.

Revision ID: 0002_v5_foundations
Revises: 0001_baseline
Create Date: 2026-09-22 16:22:16.637090

"""
from datetime import date
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002_v5_foundations'
down_revision: Union[str, Sequence[str], None] = '0001_baseline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Kept in sync by hand with app/seed_data/rule_sets.py's RACE_RULE_SETS[0] — the migration must
# not import application code, so the one row this migration needs is duplicated here narrowly
# (id/effective_from/source_url/notes only, never the station definitions themselves).
_RULE_SET_ID = "hyrox_singles_2026_27"
_RULE_SET_EFFECTIVE_FROM = date(2026, 1, 1)
_RULE_SET_SOURCE_URL = "https://hyrox.com/rulebook/"
_RULE_SET_NOTES = "2026/27 season singles rulebook + division weight charts."


def upgrade() -> None:
    op.create_table(
        'race_rule_sets',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('source_url', sa.String(), nullable=False),
        sa.Column('notes', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'athlete_equipment_profiles',
        sa.Column('athlete_id', sa.String(), nullable=False),
        sa.Column('available_equipment', sa.JSON(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['athlete_id'], ['athletes.id']),
        sa.PrimaryKeyConstraint('athlete_id'),
    )
    op.create_table(
        'scheduling_constraints',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('athlete_id', sa.String(), nullable=False),
        sa.Column('day_of_week', sa.Integer(), nullable=False),
        sa.Column('available', sa.Boolean(), nullable=False),
        sa.Column('max_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('notes', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['athlete_id'], ['athletes.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_scheduling_constraints_athlete_id'), 'scheduling_constraints', ['athlete_id'], unique=False)
    op.create_table(
        'programme_decisions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('athlete_id', sa.String(), nullable=False),
        sa.Column('training_week_id', sa.String(), nullable=True),
        sa.Column('athlete_session_id', sa.String(), nullable=True),
        sa.Column('decision_type', sa.String(), nullable=False),
        sa.Column('summary', sa.String(), nullable=False),
        sa.Column('before_state', sa.JSON(), nullable=True),
        sa.Column('after_state', sa.JSON(), nullable=True),
        sa.Column('schema_version', sa.String(), nullable=False),
        sa.Column('rule_set_version', sa.String(), nullable=True),
        sa.Column('evidence_class', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['athlete_id'], ['athletes.id']),
        sa.ForeignKeyConstraint(['athlete_session_id'], ['workouts.id']),
        sa.ForeignKeyConstraint(['rule_set_version'], ['race_rule_sets.id']),
        sa.ForeignKeyConstraint(['training_week_id'], ['training_weeks.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_programme_decisions_athlete_id'), 'programme_decisions', ['athlete_id'], unique=False)

    with op.batch_alter_table('station_reference', schema=None) as batch_op:
        batch_op.add_column(sa.Column('rule_set_version', sa.String(), nullable=True))
        batch_op.create_foreign_key(
            'fk_station_reference_rule_set_version', 'race_rule_sets', ['rule_set_version'], ['id']
        )

    # --- Ruleset data migration: insert the one real RaceRuleSet row, then backfill + verify ---
    conn = op.get_bind()
    race_rule_sets = sa.table(
        'race_rule_sets',
        sa.column('id', sa.String()),
        sa.column('effective_from', sa.Date()),
        sa.column('source_url', sa.String()),
        sa.column('notes', sa.String()),
    )
    station_reference = sa.table(
        'station_reference',
        sa.column('slug', sa.String()),
        sa.column('rule_set_version', sa.String()),
    )

    conn.execute(
        race_rule_sets.insert().values(
            id=_RULE_SET_ID,
            effective_from=_RULE_SET_EFFECTIVE_FROM,
            source_url=_RULE_SET_SOURCE_URL,
            notes=_RULE_SET_NOTES,
        )
    )
    conn.execute(
        station_reference.update()
        .where(station_reference.c.rule_set_version.is_(None))
        .values(rule_set_version=_RULE_SET_ID)
    )
    remaining = conn.execute(
        sa.select(sa.func.count())
        .select_from(station_reference)
        .where(station_reference.c.rule_set_version.is_(None))
    ).scalar()
    if remaining:
        raise RuntimeError(
            f"0002_v5_foundations: {remaining} station_reference row(s) left without a rule_set_version after backfill."
        )


def downgrade() -> None:
    with op.batch_alter_table('station_reference', schema=None) as batch_op:
        batch_op.drop_constraint('fk_station_reference_rule_set_version', type_='foreignkey')
        batch_op.drop_column('rule_set_version')

    op.drop_index(op.f('ix_programme_decisions_athlete_id'), table_name='programme_decisions')
    op.drop_table('programme_decisions')
    op.drop_index(op.f('ix_scheduling_constraints_athlete_id'), table_name='scheduling_constraints')
    op.drop_table('scheduling_constraints')
    op.drop_table('athlete_equipment_profiles')
    op.drop_table('race_rule_sets')
