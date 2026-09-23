"""capability foundation — Program Engine v5 Milestone 1B.

Fourteen new tables implementing the approved Milestone 1B plan: CapabilityDefinition and
CapabilityMetric (immutable seed definitions); CapabilityAssessment (immutable evidence,
source-linked with composite FKs enforcing athlete ownership against BenchmarkResult/
RecoveryReading/PastHyroxResult); CapabilityScore/CapabilityScoreAssessment/CapabilityGap
(append-only measurement -> lineage -> interpretation, linked by composite FKs so a score or
gap can never cite another athlete's or another metric's evidence); CapabilityBandPolicy/
CapabilityBand and CapabilityConfidencePolicy/CapabilityConfidenceRule (versioned config,
seeded empty — no thresholds in this migration); BenchmarkDefinition/BenchmarkDefinitionMetric/
BenchmarkResult; and AthleteStatusReport (isolated symptom/pain capture, no FK into the
capability-scoring layer).

Also adds an additive UNIQUE(id, athlete_id) to the two EXISTING tables CapabilityAssessment's
composite FKs need to target — recovery_readings and past_hyrox_results — via batch_alter_table
(SQLite can't ALTER TABLE ADD CONSTRAINT outside batch mode, same as 0003_1a_hardening). These
two constraint additions run BEFORE capability_assessments is created, since its composite FKs
reference them.

Purely additive throughout — downgrade() drops exactly what upgrade() created.

Revision ID: 0004_capability_foundation
Revises: 0003_1a_hardening
Create Date: 2026-09-22 20:31:31.039156

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004_capability_foundation'
down_revision: Union[str, Sequence[str], None] = '0003_1a_hardening'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Must run BEFORE capability_assessments is created — its composite FKs target these.
    with op.batch_alter_table('recovery_readings', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_recovery_readings_id_athlete_id', ['id', 'athlete_id'])
    with op.batch_alter_table('past_hyrox_results', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_past_hyrox_results_id_athlete_id', ['id', 'athlete_id'])

    op.create_table('benchmark_definitions',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('protocol_description', sa.Text(), nullable=False),
    sa.Column('unit', sa.String(), nullable=False),
    sa.Column('evidence_class', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('capability_definitions',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('measurement_hint', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('athlete_status_reports',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('athlete_id', sa.String(), nullable=False),
    sa.Column('recorded_at', sa.DateTime(), nullable=False),
    sa.Column('source', sa.String(), nullable=False),
    sa.Column('pain_present', sa.Boolean(), nullable=False),
    sa.Column('symptom_severity', sa.String(), nullable=True),
    sa.Column('body_area', sa.String(), nullable=True),
    sa.Column('illness_present', sa.Boolean(), nullable=False),
    sa.Column('effect_on_training', sa.String(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.CheckConstraint("effect_on_training NOT IN ('reduced', 'avoid') OR pain_present = TRUE OR illness_present = TRUE"),
    sa.CheckConstraint("pain_present = TRUE OR illness_present = TRUE OR effect_on_training IS NULL OR effect_on_training = 'none'"),
    sa.CheckConstraint("pain_present = TRUE OR symptom_severity IS NULL OR symptom_severity = 'none'"),
    sa.CheckConstraint("source = 'athlete_self_report'", name='ck_athlete_status_report_source'),
    sa.ForeignKeyConstraint(['athlete_id'], ['athletes.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('benchmark_results',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('athlete_id', sa.String(), nullable=False),
    sa.Column('benchmark_id', sa.String(), nullable=False),
    sa.Column('completed_at', sa.DateTime(), nullable=False),
    sa.Column('raw_value', sa.Float(), nullable=False),
    sa.Column('context', sa.JSON(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['athlete_id'], ['athletes.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['benchmark_id'], ['benchmark_definitions.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'athlete_id')
    )
    op.create_table('capability_metrics',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('capability_id', sa.String(), nullable=False),
    sa.Column('station', sa.String(), nullable=True),
    sa.Column('unit', sa.String(), nullable=False),
    sa.Column('higher_is_better', sa.Boolean(), nullable=False),
    sa.Column('evidence_class', sa.String(), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['capability_id'], ['capability_definitions.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('benchmark_definition_metrics',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('benchmark_id', sa.String(), nullable=False),
    sa.Column('metric_id', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['benchmark_id'], ['benchmark_definitions.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['metric_id'], ['capability_metrics.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('benchmark_id', 'metric_id')
    )
    op.create_table('capability_band_policies',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('metric_id', sa.String(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('hysteresis_margin_pct', sa.Float(), nullable=True),
    sa.Column('hysteresis_repeat_count', sa.Integer(), nullable=True),
    sa.Column('effective_from', sa.Date(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=False),
    sa.Column('evidence_class', sa.String(), nullable=False),
    sa.CheckConstraint('hysteresis_margin_pct IS NULL OR hysteresis_margin_pct >= 0'),
    sa.CheckConstraint('hysteresis_repeat_count IS NULL OR hysteresis_repeat_count > 0'),
    sa.CheckConstraint('version > 0'),
    sa.ForeignKeyConstraint(['metric_id'], ['capability_metrics.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'metric_id'),
    sa.UniqueConstraint('metric_id', 'version')
    )
    op.create_table('capability_confidence_policies',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('metric_id', sa.String(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('effective_from', sa.Date(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=False),
    sa.CheckConstraint('version > 0'),
    sa.ForeignKeyConstraint(['metric_id'], ['capability_metrics.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('metric_id', 'version')
    )
    op.create_table('capability_scores',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('athlete_id', sa.String(), nullable=False),
    sa.Column('metric_id', sa.String(), nullable=False),
    sa.Column('value', sa.Float(), nullable=False),
    sa.Column('computation_method', sa.String(), nullable=False),
    sa.Column('evidence_class', sa.String(), nullable=False),
    sa.Column('computed_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['athlete_id'], ['athletes.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['metric_id'], ['capability_metrics.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'athlete_id', 'metric_id')
    )
    op.create_table('capability_bands',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('band_policy_id', sa.String(), nullable=False),
    sa.Column('label', sa.String(), nullable=False),
    sa.Column('lower_bound', sa.Float(), nullable=True),
    sa.Column('lower_inclusive', sa.Boolean(), nullable=False),
    sa.Column('upper_bound', sa.Float(), nullable=True),
    sa.Column('upper_inclusive', sa.Boolean(), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.CheckConstraint('lower_bound IS NOT NULL OR upper_bound IS NOT NULL'),
    sa.CheckConstraint('lower_bound IS NULL OR upper_bound IS NULL OR lower_bound < upper_bound'),
    sa.ForeignKeyConstraint(['band_policy_id'], ['capability_band_policies.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('band_policy_id', 'label'),
    sa.UniqueConstraint('band_policy_id', 'sort_order')
    )
    op.create_table('capability_confidence_rules',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('confidence_policy_id', sa.String(), nullable=False),
    sa.Column('source_quality_tier', sa.String(), nullable=False),
    sa.Column('recency_window_days', sa.Integer(), nullable=False),
    sa.Column('min_data_points', sa.Integer(), nullable=False),
    sa.Column('requires_corroboration', sa.Boolean(), nullable=False),
    sa.Column('min_corroborating_count', sa.Integer(), nullable=True),
    sa.Column('resulting_confidence_tier', sa.String(), nullable=False),
    sa.Column('evaluation_order', sa.Integer(), nullable=False),
    sa.CheckConstraint('(requires_corroboration = FALSE AND min_corroborating_count IS NULL) OR (requires_corroboration = TRUE AND min_corroborating_count IS NOT NULL AND min_corroborating_count > 0)', name='ck_capability_confidence_rule_corroboration_consistency'),
    sa.CheckConstraint('evaluation_order >= 0'),
    sa.CheckConstraint('min_data_points > 0'),
    sa.CheckConstraint('recency_window_days > 0'),
    sa.ForeignKeyConstraint(['confidence_policy_id'], ['capability_confidence_policies.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('confidence_policy_id', 'source_quality_tier', 'evaluation_order'),
    sa.UniqueConstraint('confidence_policy_id', 'source_quality_tier', 'resulting_confidence_tier')
    )
    op.create_table('capability_gaps',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('athlete_id', sa.String(), nullable=False),
    sa.Column('metric_id', sa.String(), nullable=False),
    sa.Column('classification', sa.String(), nullable=False),
    sa.Column('confidence', sa.String(), nullable=False),
    sa.Column('based_on_score_id', sa.String(), nullable=False),
    sa.Column('band_policy_id', sa.String(), nullable=True),
    sa.Column('reasoning', sa.Text(), nullable=False),
    sa.Column('flagged_for_reassessment', sa.Boolean(), nullable=False),
    sa.Column('flag_reason', sa.Text(), nullable=True),
    sa.Column('computed_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint("(classification = 'unclassified' AND band_policy_id IS NULL AND confidence = 'none') OR (classification != 'unclassified' AND band_policy_id IS NOT NULL AND confidence != 'none')", name='ck_capability_gap_classification_consistency'),
    sa.CheckConstraint('(flagged_for_reassessment = FALSE AND flag_reason IS NULL) OR (flagged_for_reassessment = TRUE AND flag_reason IS NOT NULL)', name='ck_capability_gap_flag_reason_consistency'),
    sa.ForeignKeyConstraint(['band_policy_id', 'metric_id'], ['capability_band_policies.id', 'capability_band_policies.metric_id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['based_on_score_id', 'athlete_id', 'metric_id'], ['capability_scores.id', 'capability_scores.athlete_id', 'capability_scores.metric_id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('capability_assessments',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('athlete_id', sa.String(), nullable=False),
    sa.Column('metric_id', sa.String(), nullable=False),
    sa.Column('raw_value', sa.Float(), nullable=False),
    sa.Column('derivation_method', sa.String(), nullable=True),
    sa.Column('assessment_type', sa.String(), nullable=False),
    sa.Column('benchmark_result_id', sa.String(), nullable=True),
    sa.Column('workout_id', sa.String(), nullable=True),
    sa.Column('recovery_reading_id', sa.String(), nullable=True),
    sa.Column('past_hyrox_result_id', sa.String(), nullable=True),
    sa.Column('division', sa.String(), nullable=True),
    sa.Column('rule_set_version_id', sa.String(), nullable=True),
    sa.Column('context_note', sa.Text(), nullable=True),
    sa.Column('recorded_at', sa.DateTime(), nullable=False),
    sa.Column('evidence_class', sa.String(), nullable=False),
    sa.CheckConstraint("(assessment_type = 'benchmark_result' AND benchmark_result_id IS NOT NULL AND workout_id IS NULL AND recovery_reading_id IS NULL AND past_hyrox_result_id IS NULL) OR (assessment_type = 'logged_session_derived' AND workout_id IS NOT NULL AND benchmark_result_id IS NULL AND recovery_reading_id IS NULL AND past_hyrox_result_id IS NULL) OR (assessment_type = 'wearable_derived' AND recovery_reading_id IS NOT NULL AND benchmark_result_id IS NULL AND workout_id IS NULL AND past_hyrox_result_id IS NULL) OR (assessment_type = 'race_result' AND past_hyrox_result_id IS NOT NULL AND benchmark_result_id IS NULL AND workout_id IS NULL AND recovery_reading_id IS NULL) OR (assessment_type = 'self_report' AND benchmark_result_id IS NULL AND workout_id IS NULL AND recovery_reading_id IS NULL AND past_hyrox_result_id IS NULL)", name='ck_capability_assessment_source_consistency'),
    sa.CheckConstraint("assessment_type != 'logged_session_derived' OR derivation_method IS NOT NULL"),
    sa.CheckConstraint("assessment_type != 'self_report' OR derivation_method IS NULL"),
    sa.ForeignKeyConstraint(['athlete_id'], ['athletes.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['benchmark_result_id', 'athlete_id'], ['benchmark_results.id', 'benchmark_results.athlete_id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['metric_id'], ['capability_metrics.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['past_hyrox_result_id', 'athlete_id'], ['past_hyrox_results.id', 'past_hyrox_results.athlete_id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['recovery_reading_id', 'athlete_id'], ['recovery_readings.id', 'recovery_readings.athlete_id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['rule_set_version_id'], ['race_rule_sets.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['workout_id'], ['workouts.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'athlete_id', 'metric_id')
    )
    op.create_table('capability_score_assessments',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('score_id', sa.String(), nullable=False),
    sa.Column('assessment_id', sa.String(), nullable=False),
    sa.Column('athlete_id', sa.String(), nullable=False),
    sa.Column('metric_id', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['assessment_id', 'athlete_id', 'metric_id'], ['capability_assessments.id', 'capability_assessments.athlete_id', 'capability_assessments.metric_id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['score_id', 'athlete_id', 'metric_id'], ['capability_scores.id', 'capability_scores.athlete_id', 'capability_scores.metric_id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('score_id', 'assessment_id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('capability_score_assessments')
    op.drop_table('capability_assessments')
    op.drop_table('capability_gaps')
    op.drop_table('capability_confidence_rules')
    op.drop_table('capability_bands')
    op.drop_table('capability_scores')
    op.drop_table('capability_confidence_policies')
    op.drop_table('capability_band_policies')
    op.drop_table('benchmark_definition_metrics')
    op.drop_table('capability_metrics')
    op.drop_table('benchmark_results')
    op.drop_table('athlete_status_reports')
    op.drop_table('capability_definitions')
    op.drop_table('benchmark_definitions')

    with op.batch_alter_table('past_hyrox_results', schema=None) as batch_op:
        batch_op.drop_constraint('uq_past_hyrox_results_id_athlete_id', type_='unique')
    with op.batch_alter_table('recovery_readings', schema=None) as batch_op:
        batch_op.drop_constraint('uq_recovery_readings_id_athlete_id', type_='unique')
