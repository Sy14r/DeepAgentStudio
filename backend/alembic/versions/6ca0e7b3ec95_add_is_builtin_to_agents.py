"""add_is_builtin_to_agents

Revision ID: 6ca0e7b3ec95
Revises: a1b2c3d4e5f6
Create Date: 2026-01-07 03:33:06.264448

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6ca0e7b3ec95'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_builtin column to agents table
    op.add_column('agents', sa.Column('is_builtin', sa.Boolean(), nullable=False, server_default='false'))

    # Make user_id nullable for built-in agents
    op.alter_column('agents', 'user_id',
               existing_type=sa.INTEGER(),
               nullable=True)

    # Add index for is_builtin
    op.create_index(op.f('ix_agents_is_builtin'), 'agents', ['is_builtin'], unique=False)


def downgrade() -> None:
    # Remove index
    op.drop_index(op.f('ix_agents_is_builtin'), table_name='agents')

    # Make user_id not nullable again
    op.alter_column('agents', 'user_id',
               existing_type=sa.INTEGER(),
               nullable=False)

    # Remove is_builtin column
    op.drop_column('agents', 'is_builtin')
