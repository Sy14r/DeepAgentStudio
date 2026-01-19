"""add_agent_permissions_table

Revision ID: j0k1l2m3n4o5
Revises: i9j0k1l2m3n4
Create Date: 2026-01-18 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'j0k1l2m3n4o5'
down_revision: Union[str, None] = 'i9j0k1l2m3n4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create agent_permissions table with String preset (more portable than Enum)
    op.create_table(
        'agent_permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=False),
        sa.Column('preset', sa.String(50), nullable=False, server_default='observer'),
        sa.Column('custom_permissions', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_agent_permissions_id', 'agent_permissions', ['id'], unique=False)
    op.create_index('ix_agent_permissions_agent_id', 'agent_permissions', ['agent_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_agent_permissions_agent_id', table_name='agent_permissions')
    op.drop_index('ix_agent_permissions_id', table_name='agent_permissions')
    op.drop_table('agent_permissions')
