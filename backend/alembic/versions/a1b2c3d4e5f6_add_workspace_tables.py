"""add_workspace_tables

Revision ID: a1b2c3d4e5f6
Revises: f86b4e299bda
Create Date: 2026-01-06 22:00:00.000000

Adds tables for Advanced Agent Toolkit:
- session_workspaces: Isolated file storage per session
- session_tasks: Task list for tracking progress
- session_scratchpads: Working notes and intermediate thoughts
- search_provider_configs: Web search API configuration
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f86b4e299bda'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Define enum types
task_status_enum = postgresql.ENUM('pending', 'in_progress', 'completed', 'blocked', name='taskstatus', create_type=False)
search_provider_type_enum = postgresql.ENUM('serper', 'tavily', 'serpapi', name='searchprovidertype', create_type=False)


def upgrade() -> None:
    bind = op.get_bind()

    # Create task_status enum
    result = bind.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'taskstatus'"))
    if not result.fetchone():
        task_status_enum.create(bind, checkfirst=True)

    # Create search_provider_type enum
    result = bind.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'searchprovidertype'"))
    if not result.fetchone():
        search_provider_type_enum.create(bind, checkfirst=True)

    # Create session_workspaces table
    op.create_table('session_workspaces',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('workspace_path', sa.String(length=255), nullable=False),
        sa.Column('total_size_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('file_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id')
    )
    op.create_index(op.f('ix_session_workspaces_id'), 'session_workspaces', ['id'], unique=False)
    op.create_index(op.f('ix_session_workspaces_session_id'), 'session_workspaces', ['session_id'], unique=True)

    # Create session_tasks table
    op.create_table('session_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('task_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', task_status_enum, nullable=False, server_default='pending'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'task_number', name='uq_session_task_number')
    )
    op.create_index(op.f('ix_session_tasks_id'), 'session_tasks', ['id'], unique=False)
    op.create_index(op.f('ix_session_tasks_session_id'), 'session_tasks', ['session_id'], unique=False)
    op.create_index(op.f('ix_session_tasks_status'), 'session_tasks', ['status'], unique=False)

    # Create session_scratchpads table
    op.create_table('session_scratchpads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('section', sa.String(length=100), nullable=False, server_default='default'),
        sa.Column('content', sa.Text(), nullable=False, server_default=''),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'section', name='uq_session_scratchpad_section')
    )
    op.create_index(op.f('ix_session_scratchpads_id'), 'session_scratchpads', ['id'], unique=False)
    op.create_index(op.f('ix_session_scratchpads_session_id'), 'session_scratchpads', ['session_id'], unique=False)

    # Create search_provider_configs table
    op.create_table('search_provider_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('provider_type', search_provider_type_enum, nullable=False),
        sa.Column('api_key_encrypted', sa.String(length=500), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('default_num_results', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('total_searches', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_search_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_search_provider_configs_id'), 'search_provider_configs', ['id'], unique=False)
    op.create_index(op.f('ix_search_provider_configs_user_id'), 'search_provider_configs', ['user_id'], unique=True)
    op.create_index(op.f('ix_search_provider_configs_provider_type'), 'search_provider_configs', ['provider_type'], unique=False)


def downgrade() -> None:
    # Drop search_provider_configs table
    op.drop_index(op.f('ix_search_provider_configs_provider_type'), table_name='search_provider_configs')
    op.drop_index(op.f('ix_search_provider_configs_user_id'), table_name='search_provider_configs')
    op.drop_index(op.f('ix_search_provider_configs_id'), table_name='search_provider_configs')
    op.drop_table('search_provider_configs')

    # Drop session_scratchpads table
    op.drop_index(op.f('ix_session_scratchpads_session_id'), table_name='session_scratchpads')
    op.drop_index(op.f('ix_session_scratchpads_id'), table_name='session_scratchpads')
    op.drop_table('session_scratchpads')

    # Drop session_tasks table
    op.drop_index(op.f('ix_session_tasks_status'), table_name='session_tasks')
    op.drop_index(op.f('ix_session_tasks_session_id'), table_name='session_tasks')
    op.drop_index(op.f('ix_session_tasks_id'), table_name='session_tasks')
    op.drop_table('session_tasks')

    # Drop session_workspaces table
    op.drop_index(op.f('ix_session_workspaces_session_id'), table_name='session_workspaces')
    op.drop_index(op.f('ix_session_workspaces_id'), table_name='session_workspaces')
    op.drop_table('session_workspaces')

    # Drop enum types
    task_status_enum.drop(op.get_bind(), checkfirst=True)
    search_provider_type_enum.drop(op.get_bind(), checkfirst=True)
