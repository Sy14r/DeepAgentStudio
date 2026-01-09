"""Add evaluation tables

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-01-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Evaluation Datasets
    op.create_table(
        'evaluation_datasets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('schema_type', sa.String(20), nullable=False, server_default='text'),
        sa.Column('input_schema', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('output_schema', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String(255)), nullable=True),
        sa.Column('example_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_evaluation_datasets_user', 'evaluation_datasets', ['user_id'])

    # Dataset Examples
    op.create_table(
        'dataset_examples',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dataset_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('input', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('expected_output', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('example_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String(255)), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['dataset_id'], ['evaluation_datasets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_dataset_examples_dataset', 'dataset_examples', ['dataset_id'])

    # Evaluators
    op.create_table(
        'evaluators',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),  # NULL for built-in
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('category', sa.String(20), nullable=False, server_default='output'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('is_builtin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_evaluators_user', 'evaluators', ['user_id'])
    op.create_index('idx_evaluators_type', 'evaluators', ['type'])
    op.create_index('idx_evaluators_category', 'evaluators', ['category'])

    # Evaluation Runs
    op.create_table(
        'evaluation_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('dataset_id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=False),
        sa.Column('agent_version_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_examples', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completed_examples', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['dataset_id'], ['evaluation_datasets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['agent_version_id'], ['agent_versions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_evaluation_runs_user', 'evaluation_runs', ['user_id'])
    op.create_index('idx_evaluation_runs_dataset', 'evaluation_runs', ['dataset_id'])
    op.create_index('idx_evaluation_runs_agent', 'evaluation_runs', ['agent_id'])
    op.create_index('idx_evaluation_runs_status', 'evaluation_runs', ['status'])

    # Evaluation Run Evaluators (many-to-many)
    op.create_table(
        'evaluation_run_evaluators',
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('evaluator_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['evaluation_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evaluator_id'], ['evaluators.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('run_id', 'evaluator_id')
    )

    # Evaluation Results (per example)
    op.create_table(
        'evaluation_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('example_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=True),
        sa.Column('agent_output', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('run_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('token_usage_input', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('token_usage_output', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['evaluation_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['example_id'], ['dataset_examples.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_evaluation_results_run', 'evaluation_results', ['run_id'])
    op.create_index('idx_evaluation_results_example', 'evaluation_results', ['example_id'])
    op.create_index('idx_evaluation_results_status', 'evaluation_results', ['status'])

    # Evaluation Scores (per evaluator per result)
    op.create_table(
        'evaluation_scores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('result_id', sa.Integer(), nullable=False),
        sa.Column('evaluator_id', sa.Integer(), nullable=False),
        sa.Column('score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('passed', sa.Boolean(), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('score_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['result_id'], ['evaluation_results.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evaluator_id'], ['evaluators.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_evaluation_scores_result', 'evaluation_scores', ['result_id'])
    op.create_index('idx_evaluation_scores_evaluator', 'evaluation_scores', ['evaluator_id'])


def downgrade() -> None:
    op.drop_table('evaluation_scores')
    op.drop_table('evaluation_results')
    op.drop_table('evaluation_run_evaluators')
    op.drop_table('evaluation_runs')
    op.drop_table('evaluators')
    op.drop_table('dataset_examples')
    op.drop_table('evaluation_datasets')
