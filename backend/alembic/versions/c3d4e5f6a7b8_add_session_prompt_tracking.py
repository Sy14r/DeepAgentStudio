"""add_session_prompt_tracking

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-01-07 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add prompt_version_id column to sessions table to track which prompt version was used
    op.add_column('sessions', sa.Column('prompt_version_id', sa.Integer(), nullable=True))

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_sessions_prompt_version_id',
        'sessions', 'prompt_versions',
        ['prompt_version_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add index for better query performance
    op.create_index(op.f('ix_sessions_prompt_version_id'), 'sessions', ['prompt_version_id'], unique=False)


def downgrade() -> None:
    # Remove index
    op.drop_index(op.f('ix_sessions_prompt_version_id'), table_name='sessions')

    # Remove foreign key constraint
    op.drop_constraint('fk_sessions_prompt_version_id', 'sessions', type_='foreignkey')

    # Remove column
    op.drop_column('sessions', 'prompt_version_id')
