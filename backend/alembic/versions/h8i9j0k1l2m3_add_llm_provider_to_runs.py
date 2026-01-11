"""Add llm_provider_id to evaluation_runs

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-01-10

This migration adds llm_provider_id to evaluation_runs table to allow
specifying which LLM provider to use for LLM-based evaluators (LLM Judge,
Semantic Similarity) at run time instead of requiring it in evaluator config.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h8i9j0k1l2m3'
down_revision: Union[str, None] = 'g7h8i9j0k1l2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add llm_provider_id column to evaluation_runs table
    op.add_column(
        'evaluation_runs',
        sa.Column(
            'llm_provider_id',
            sa.Integer(),
            sa.ForeignKey('llm_provider_configs.id', ondelete='SET NULL'),
            nullable=True
        )
    )

    # Create index for faster lookups
    op.create_index(
        'ix_evaluation_runs_llm_provider_id',
        'evaluation_runs',
        ['llm_provider_id']
    )


def downgrade() -> None:
    # Drop the index first
    op.drop_index('ix_evaluation_runs_llm_provider_id', table_name='evaluation_runs')

    # Drop the column
    op.drop_column('evaluation_runs', 'llm_provider_id')
