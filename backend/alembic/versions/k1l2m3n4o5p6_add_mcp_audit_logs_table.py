"""add_mcp_audit_logs_table

Revision ID: k1l2m3n4o5p6
Revises: j0k1l2m3n4o5
Create Date: 2026-01-18 18:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'k1l2m3n4o5p6'
down_revision: Union[str, None] = 'j0k1l2m3n4o5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'mcp_audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.Integer(), nullable=True),
        sa.Column('tool_name', sa.String(100), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_code', sa.String(50), nullable=True),
        sa.Column('request_summary', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id']),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_mcp_audit_logs_id', 'mcp_audit_logs', ['id'], unique=False)
    op.create_index('ix_mcp_audit_logs_user_id', 'mcp_audit_logs', ['user_id'], unique=False)
    op.create_index('ix_mcp_audit_logs_agent_id', 'mcp_audit_logs', ['agent_id'], unique=False)
    op.create_index('ix_mcp_audit_logs_created_at', 'mcp_audit_logs', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_mcp_audit_logs_created_at', table_name='mcp_audit_logs')
    op.drop_index('ix_mcp_audit_logs_agent_id', table_name='mcp_audit_logs')
    op.drop_index('ix_mcp_audit_logs_user_id', table_name='mcp_audit_logs')
    op.drop_index('ix_mcp_audit_logs_id', table_name='mcp_audit_logs')
    op.drop_table('mcp_audit_logs')
