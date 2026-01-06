"""add_mcp_server_configs_table

Revision ID: e8c3f7a2b591
Revises: cb75d39778cb
Create Date: 2026-01-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e8c3f7a2b591'
down_revision: Union[str, None] = 'cb75d39778cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Define the enum type
mcp_transport_type_enum = postgresql.ENUM('stdio', 'sse', 'streamable_http', name='mcptransporttype', create_type=False)


def upgrade() -> None:
    # Create MCP transport type enum (only if it doesn't exist)
    bind = op.get_bind()
    # Check if the enum already exists
    result = bind.execute(sa.text(
        "SELECT 1 FROM pg_type WHERE typname = 'mcptransporttype'"
    ))
    if not result.fetchone():
        mcp_transport_type_enum.create(bind, checkfirst=True)

    # Create mcp_server_configs table
    op.create_table('mcp_server_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('transport_type', mcp_transport_type_enum, nullable=False),
        sa.Column('stdio_config', sa.JSON(), nullable=True),
        sa.Column('http_config', sa.JSON(), nullable=True),
        sa.Column('encrypted_env_vars', sa.Text(), nullable=True),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('cached_tools', sa.JSON(), nullable=True),
        sa.Column('tools_last_discovered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('last_connected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_mcp_server_configs_id'), 'mcp_server_configs', ['id'], unique=False)
    op.create_index(op.f('ix_mcp_server_configs_user_id'), 'mcp_server_configs', ['user_id'], unique=False)
    op.create_index(op.f('ix_mcp_server_configs_transport_type'), 'mcp_server_configs', ['transport_type'], unique=False)

    # Create agent_mcp_servers association table
    op.create_table('agent_mcp_servers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=False),
        sa.Column('mcp_server_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['mcp_server_id'], ['mcp_server_configs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_mcp_servers_agent_id'), 'agent_mcp_servers', ['agent_id'], unique=False)
    op.create_index(op.f('ix_agent_mcp_servers_mcp_server_id'), 'agent_mcp_servers', ['mcp_server_id'], unique=False)


def downgrade() -> None:
    # Drop agent_mcp_servers table
    op.drop_index(op.f('ix_agent_mcp_servers_mcp_server_id'), table_name='agent_mcp_servers')
    op.drop_index(op.f('ix_agent_mcp_servers_agent_id'), table_name='agent_mcp_servers')
    op.drop_table('agent_mcp_servers')

    # Drop mcp_server_configs table
    op.drop_index(op.f('ix_mcp_server_configs_transport_type'), table_name='mcp_server_configs')
    op.drop_index(op.f('ix_mcp_server_configs_user_id'), table_name='mcp_server_configs')
    op.drop_index(op.f('ix_mcp_server_configs_id'), table_name='mcp_server_configs')
    op.drop_table('mcp_server_configs')

    # Drop enum type
    mcp_transport_type_enum.drop(op.get_bind(), checkfirst=True)
