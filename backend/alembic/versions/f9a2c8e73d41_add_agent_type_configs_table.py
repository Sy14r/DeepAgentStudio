"""add_agent_type_configs_table

Revision ID: f9a2c8e73d41
Revises: e8c3f7a2b591
Create Date: 2026-01-06 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f9a2c8e73d41'
down_revision: Union[str, None] = 'e8c3f7a2b591'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Define the execution strategy enum type
execution_strategy_enum = postgresql.ENUM('react', 'plan_and_execute', 'conversational', name='executionstrategy', create_type=False)


def upgrade() -> None:
    bind = op.get_bind()

    # Create execution_strategy enum (only if it doesn't exist)
    result = bind.execute(sa.text(
        "SELECT 1 FROM pg_type WHERE typname = 'executionstrategy'"
    ))
    if not result.fetchone():
        execution_strategy_enum.create(bind, checkfirst=True)

    # Create agent_type_configs table
    op.create_table('agent_type_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('execution_strategy', execution_strategy_enum, nullable=False),
        sa.Column('system_prompt_template', sa.Text(), nullable=True),
        sa.Column('default_llm_config', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('default_memory_config', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('max_iterations', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('is_builtin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_type_configs_id'), 'agent_type_configs', ['id'], unique=False)
    op.create_index(op.f('ix_agent_type_configs_name'), 'agent_type_configs', ['name'], unique=False)
    op.create_index(op.f('ix_agent_type_configs_user_id'), 'agent_type_configs', ['user_id'], unique=False)

    # Create agent_type_recommended_tools association table
    op.create_table('agent_type_recommended_tools',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_type_id', sa.Integer(), nullable=False),
        sa.Column('tool_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agent_type_id'], ['agent_type_configs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tool_id'], ['tools.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_type_recommended_tools_agent_type_id'), 'agent_type_recommended_tools', ['agent_type_id'], unique=False)
    op.create_index(op.f('ix_agent_type_recommended_tools_tool_id'), 'agent_type_recommended_tools', ['tool_id'], unique=False)

    # Seed builtin agent types
    op.execute("""
        INSERT INTO agent_type_configs (name, description, icon, execution_strategy, system_prompt_template, default_llm_config, default_memory_config, max_iterations, is_builtin, is_active)
        VALUES
        ('ReAct', 'Reasoning and Acting agent that uses tools to solve problems step by step. Best for tasks requiring tool usage and iterative reasoning.', 'brain', 'react', 'You are a helpful AI assistant. Think step by step and use available tools when needed to accomplish tasks.', '{"temperature": 0.7, "max_tokens": 4096}', '{"type": "buffer", "context_window": 10}', 10, true, true),
        ('Plan-and-Execute', 'Agent that first creates a comprehensive plan, then executes each step systematically. Best for complex multi-step tasks.', 'list-checks', 'plan_and_execute', 'You are a strategic AI assistant. First, create a comprehensive plan to accomplish the user''s goal, then execute each step systematically.', '{"temperature": 0.5, "max_tokens": 4096}', '{"type": "buffer", "context_window": 20}', 15, true, true),
        ('Conversational', 'Simple conversational agent without tool use. Ideal for chat, Q&A, and discussions that do not require external tools.', 'message-circle', 'conversational', 'You are a friendly and helpful AI assistant. Engage in natural conversation and provide helpful, accurate responses.', '{"temperature": 0.8, "max_tokens": 2048}', '{"type": "buffer", "context_window": 10}', 1, true, true)
    """)

    # Add agent_type_id column to agents table (nullable first for migration)
    op.add_column('agents', sa.Column('agent_type_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_agents_agent_type_id'), 'agents', ['agent_type_id'], unique=False)

    # Migrate existing agents: map old enum values to new type IDs
    # Note: PostgreSQL stores SQLAlchemy enums by NAME (uppercase), not VALUE
    # ReAct
    op.execute("""
        UPDATE agents SET agent_type_id = (
            SELECT id FROM agent_type_configs WHERE name = 'ReAct' AND is_builtin = true
        ) WHERE agent_type = 'REACT'
    """)
    # Plan-and-Execute
    op.execute("""
        UPDATE agents SET agent_type_id = (
            SELECT id FROM agent_type_configs WHERE name = 'Plan-and-Execute' AND is_builtin = true
        ) WHERE agent_type = 'PLAN_AND_EXECUTE'
    """)
    # Conversational
    op.execute("""
        UPDATE agents SET agent_type_id = (
            SELECT id FROM agent_type_configs WHERE name = 'Conversational' AND is_builtin = true
        ) WHERE agent_type = 'CONVERSATIONAL'
    """)
    # Custom agents default to ReAct (since Custom was never fully implemented)
    op.execute("""
        UPDATE agents SET agent_type_id = (
            SELECT id FROM agent_type_configs WHERE name = 'ReAct' AND is_builtin = true
        ) WHERE agent_type = 'CUSTOM' OR agent_type_id IS NULL
    """)

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_agents_agent_type_id',
        'agents', 'agent_type_configs',
        ['agent_type_id'], ['id']
    )

    # Make agent_type_id NOT NULL now that all rows have values
    op.alter_column('agents', 'agent_type_id', nullable=False)

    # Drop the old agent_type enum column
    op.drop_column('agents', 'agent_type')

    # Drop the old agenttype enum type
    op.execute("DROP TYPE IF EXISTS agenttype")


def downgrade() -> None:
    bind = op.get_bind()

    # Recreate old agenttype enum
    agenttype_enum = postgresql.ENUM('ReAct', 'Plan-and-Execute', 'Conversational', 'Custom', name='agenttype', create_type=False)
    result = bind.execute(sa.text(
        "SELECT 1 FROM pg_type WHERE typname = 'agenttype'"
    ))
    if not result.fetchone():
        agenttype_enum.create(bind, checkfirst=True)

    # Add old agent_type column back
    op.add_column('agents', sa.Column('agent_type', agenttype_enum, nullable=True))

    # Migrate data back from agent_type_id to agent_type enum
    # Note: PostgreSQL stores SQLAlchemy enums by NAME (uppercase), not VALUE
    op.execute("""
        UPDATE agents a SET agent_type = 'REACT'
        FROM agent_type_configs atc
        WHERE a.agent_type_id = atc.id AND atc.execution_strategy = 'react'
    """)
    op.execute("""
        UPDATE agents a SET agent_type = 'PLAN_AND_EXECUTE'
        FROM agent_type_configs atc
        WHERE a.agent_type_id = atc.id AND atc.execution_strategy = 'plan_and_execute'
    """)
    op.execute("""
        UPDATE agents a SET agent_type = 'CONVERSATIONAL'
        FROM agent_type_configs atc
        WHERE a.agent_type_id = atc.id AND atc.execution_strategy = 'conversational'
    """)
    # Default any remaining to REACT
    op.execute("UPDATE agents SET agent_type = 'REACT' WHERE agent_type IS NULL")

    # Make agent_type NOT NULL
    op.alter_column('agents', 'agent_type', nullable=False)

    # Drop foreign key and agent_type_id column
    op.drop_constraint('fk_agents_agent_type_id', 'agents', type_='foreignkey')
    op.drop_index(op.f('ix_agents_agent_type_id'), table_name='agents')
    op.drop_column('agents', 'agent_type_id')

    # Drop agent_type_recommended_tools table
    op.drop_index(op.f('ix_agent_type_recommended_tools_tool_id'), table_name='agent_type_recommended_tools')
    op.drop_index(op.f('ix_agent_type_recommended_tools_agent_type_id'), table_name='agent_type_recommended_tools')
    op.drop_table('agent_type_recommended_tools')

    # Drop agent_type_configs table
    op.drop_index(op.f('ix_agent_type_configs_user_id'), table_name='agent_type_configs')
    op.drop_index(op.f('ix_agent_type_configs_name'), table_name='agent_type_configs')
    op.drop_index(op.f('ix_agent_type_configs_id'), table_name='agent_type_configs')
    op.drop_table('agent_type_configs')

    # Drop execution_strategy enum type
    execution_strategy_enum.drop(bind, checkfirst=True)
