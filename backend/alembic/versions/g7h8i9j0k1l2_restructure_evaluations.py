"""Restructure evaluations - separate config from runs

Revision ID: g7h8i9j0k1l2
Revises: f6a7b8c9d0e1
Create Date: 2026-01-09

This migration restructures the evaluation system to separate reusable
configuration (Evaluation) from execution instances (EvaluationRun).

Changes:
- Create new `evaluations` table for reusable configs
- Create new `evaluation_evaluators` junction table
- Add `evaluation_id` column to `evaluation_runs`
- Migrate existing data: each run becomes an evaluation with one run
- Drop deprecated columns (dataset_id, config) from evaluation_runs
- Drop deprecated junction table (evaluation_run_evaluators)
"""
from typing import Sequence, Union
import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'g7h8i9j0k1l2'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Create evaluations table (reusable evaluation configs)
    op.create_table(
        'evaluations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('dataset_id', sa.Integer(), nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['dataset_id'], ['evaluation_datasets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_evaluations_user', 'evaluations', ['user_id'])
    op.create_index('idx_evaluations_dataset', 'evaluations', ['dataset_id'])

    # Step 2: Create evaluation_evaluators junction table
    op.create_table(
        'evaluation_evaluators',
        sa.Column('evaluation_id', sa.Integer(), nullable=False),
        sa.Column('evaluator_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['evaluation_id'], ['evaluations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evaluator_id'], ['evaluators.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('evaluation_id', 'evaluator_id')
    )

    # Step 3: Add evaluation_id column to evaluation_runs (nullable initially)
    op.add_column(
        'evaluation_runs',
        sa.Column('evaluation_id', sa.Integer(), nullable=True)
    )

    # Step 4: Data migration - create evaluations from existing runs
    # Using raw SQL for data migration
    connection = op.get_bind()

    # Get all existing evaluation runs
    runs = connection.execute(
        sa.text("""
            SELECT id, user_id, name, dataset_id, config, created_at
            FROM evaluation_runs
            ORDER BY id
        """)
    ).fetchall()

    for run in runs:
        run_id, user_id, run_name, dataset_id, config, created_at = run

        # Create evaluation for this run
        eval_name = f"{run_name or 'Evaluation'}"

        # Serialize config dict to JSON string for PostgreSQL
        config_json = json.dumps(config) if config else '{}'

        result = connection.execute(
            sa.text("""
                INSERT INTO evaluations (user_id, name, dataset_id, config, created_at, updated_at)
                VALUES (:user_id, :name, :dataset_id, CAST(:config AS jsonb), :created_at, :created_at)
                RETURNING id
            """),
            {
                'user_id': user_id,
                'name': eval_name,
                'dataset_id': dataset_id,
                'config': config_json,
                'created_at': created_at
            }
        )
        evaluation_id = result.fetchone()[0]

        # Copy evaluator associations from run to evaluation
        connection.execute(
            sa.text("""
                INSERT INTO evaluation_evaluators (evaluation_id, evaluator_id)
                SELECT :evaluation_id, evaluator_id
                FROM evaluation_run_evaluators
                WHERE run_id = :run_id
            """),
            {'evaluation_id': evaluation_id, 'run_id': run_id}
        )

        # Link run to the new evaluation
        connection.execute(
            sa.text("""
                UPDATE evaluation_runs
                SET evaluation_id = :evaluation_id
                WHERE id = :run_id
            """),
            {'evaluation_id': evaluation_id, 'run_id': run_id}
        )

    # Step 5: Add foreign key constraint and make evaluation_id non-nullable
    op.create_foreign_key(
        'fk_evaluation_runs_evaluation',
        'evaluation_runs',
        'evaluations',
        ['evaluation_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_index('idx_evaluation_runs_evaluation', 'evaluation_runs', ['evaluation_id'])

    # Make evaluation_id non-nullable (only after data migration)
    op.alter_column('evaluation_runs', 'evaluation_id', nullable=False)

    # Step 6: Drop deprecated columns and tables
    # First drop foreign key constraints
    op.drop_constraint('evaluation_runs_dataset_id_fkey', 'evaluation_runs', type_='foreignkey')
    op.drop_index('idx_evaluation_runs_dataset', table_name='evaluation_runs')

    # Drop deprecated columns from evaluation_runs
    op.drop_column('evaluation_runs', 'dataset_id')
    op.drop_column('evaluation_runs', 'config')

    # Drop deprecated junction table
    op.drop_table('evaluation_run_evaluators')


def downgrade() -> None:
    # Step 1: Recreate the evaluation_run_evaluators table
    op.create_table(
        'evaluation_run_evaluators',
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('evaluator_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['evaluation_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evaluator_id'], ['evaluators.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('run_id', 'evaluator_id')
    )

    # Step 2: Add back deprecated columns to evaluation_runs
    op.add_column(
        'evaluation_runs',
        sa.Column('dataset_id', sa.Integer(), nullable=True)
    )
    op.add_column(
        'evaluation_runs',
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}')
    )

    # Step 3: Migrate data back from evaluations to runs
    connection = op.get_bind()

    # Copy dataset_id and config from evaluations back to runs
    connection.execute(
        sa.text("""
            UPDATE evaluation_runs r
            SET dataset_id = e.dataset_id,
                config = e.config
            FROM evaluations e
            WHERE r.evaluation_id = e.id
        """)
    )

    # Copy evaluator associations back
    connection.execute(
        sa.text("""
            INSERT INTO evaluation_run_evaluators (run_id, evaluator_id)
            SELECT r.id, ee.evaluator_id
            FROM evaluation_runs r
            JOIN evaluation_evaluators ee ON ee.evaluation_id = r.evaluation_id
        """)
    )

    # Step 4: Add back foreign key and index
    op.create_foreign_key(
        'evaluation_runs_dataset_id_fkey',
        'evaluation_runs',
        'evaluation_datasets',
        ['dataset_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_index('idx_evaluation_runs_dataset', 'evaluation_runs', ['dataset_id'])
    op.alter_column('evaluation_runs', 'dataset_id', nullable=False)

    # Step 5: Drop evaluation_id and related constraints
    op.drop_constraint('fk_evaluation_runs_evaluation', 'evaluation_runs', type_='foreignkey')
    op.drop_index('idx_evaluation_runs_evaluation', table_name='evaluation_runs')
    op.drop_column('evaluation_runs', 'evaluation_id')

    # Step 6: Drop new tables
    op.drop_table('evaluation_evaluators')
    op.drop_table('evaluations')
