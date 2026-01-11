"""Add evaluation score status and session tracking

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-01-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add status column to evaluation_scores
    op.add_column(
        'evaluation_scores',
        sa.Column('status', sa.String(20), nullable=False, server_default='completed')
    )
    op.create_index('idx_evaluation_scores_status', 'evaluation_scores', ['status'])

    # Add session_id column to evaluation_scores for evaluator session tracking
    op.add_column(
        'evaluation_scores',
        sa.Column('session_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_evaluation_scores_session',
        'evaluation_scores',
        'sessions',
        ['session_id'],
        ['id'],
        ondelete='SET NULL'
    )
    op.create_index('idx_evaluation_scores_session', 'evaluation_scores', ['session_id'])


def downgrade() -> None:
    op.drop_index('idx_evaluation_scores_session', table_name='evaluation_scores')
    op.drop_constraint('fk_evaluation_scores_session', 'evaluation_scores', type_='foreignkey')
    op.drop_column('evaluation_scores', 'session_id')
    op.drop_index('idx_evaluation_scores_status', table_name='evaluation_scores')
    op.drop_column('evaluation_scores', 'status')
