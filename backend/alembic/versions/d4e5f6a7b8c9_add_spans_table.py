"""add_spans_table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-01-07 20:00:00.000000

Enhanced tracing system with hierarchical spans for observability.
Implements Phase 1 of ENHANCED_TRACING_SPEC.md.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create span_type enum (check if exists first)
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'spantype'"))
    if not result.fetchone():
        span_type_enum = postgresql.ENUM(
            'agent', 'chain', 'llm', 'tool', 'retriever', 'embedding',
            'parser', 'prompt', 'memory', 'thought', 'error',
            name='spantype',
            create_type=True
        )
        span_type_enum.create(op.get_bind(), checkfirst=True)

    # Create span_status enum (check if exists first)
    result = conn.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'spanstatus'"))
    if not result.fetchone():
        span_status_enum = postgresql.ENUM(
            'running', 'success', 'error',
            name='spanstatus',
            create_type=True
        )
        span_status_enum.create(op.get_bind(), checkfirst=True)

    # Check if spans table already exists (partial migration recovery)
    result = conn.execute(sa.text("SELECT 1 FROM information_schema.tables WHERE table_name = 'spans'"))
    if result.fetchone():
        return  # Table already exists, skip creation

    # Reference existing enum types
    span_type_enum = postgresql.ENUM(
        'agent', 'chain', 'llm', 'tool', 'retriever', 'embedding',
        'parser', 'prompt', 'memory', 'thought', 'error',
        name='spantype',
        create_type=False
    )
    span_status_enum = postgresql.ENUM(
        'running', 'success', 'error',
        name='spanstatus',
        create_type=False
    )

    # Create spans table
    op.create_table('spans',
        # Primary key
        sa.Column('id', sa.Integer(), nullable=False),

        # Trace association
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('trace_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Hierarchy
        sa.Column('parent_span_id', sa.Integer(), nullable=True),
        sa.Column('span_order', sa.Integer(), nullable=False),
        sa.Column('depth', sa.Integer(), nullable=False, server_default='0'),

        # Identification
        sa.Column('span_type', span_type_enum, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),

        # Timing
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),

        # Status
        sa.Column('status', span_status_enum, nullable=False, server_default='running'),
        sa.Column('status_message', sa.Text(), nullable=True),

        # Data
        sa.Column('input', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('output', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # LLM-specific (nullable for non-LLM spans)
        sa.Column('model_name', sa.String(length=100), nullable=True),
        sa.Column('model_provider', sa.String(length=50), nullable=True),
        sa.Column('model_parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tokens_input', sa.Integer(), nullable=True),
        sa.Column('tokens_output', sa.Integer(), nullable=True),
        sa.Column('tokens_total', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Numeric(precision=10, scale=6), nullable=True),

        # Tool-specific (nullable for non-tool spans)
        sa.Column('tool_name', sa.String(length=255), nullable=True),

        # Error details (nullable)
        sa.Column('error_type', sa.String(length=255), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_stack', sa.Text(), nullable=True),

        # Metadata
        sa.Column('tags', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Constraints
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_span_id'], ['spans.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for common query patterns
    op.create_index(op.f('ix_spans_id'), 'spans', ['id'], unique=False)
    op.create_index(op.f('ix_spans_session_id'), 'spans', ['session_id'], unique=False)
    op.create_index('ix_spans_trace_id', 'spans', ['trace_id'], unique=False)
    op.create_index('ix_spans_parent_span_id', 'spans', ['parent_span_id'], unique=False)
    op.create_index(op.f('ix_spans_span_type'), 'spans', ['span_type'], unique=False)
    op.create_index(op.f('ix_spans_status'), 'spans', ['status'], unique=False)
    op.create_index('ix_spans_started_at', 'spans', ['started_at'], unique=False)
    op.create_index('ix_spans_tool_name', 'spans', ['tool_name'], unique=False)
    # GIN index for tags array
    op.create_index('ix_spans_tags', 'spans', ['tags'], unique=False, postgresql_using='gin')


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_spans_tags', table_name='spans', postgresql_using='gin')
    op.drop_index('ix_spans_tool_name', table_name='spans')
    op.drop_index('ix_spans_started_at', table_name='spans')
    op.drop_index(op.f('ix_spans_status'), table_name='spans')
    op.drop_index(op.f('ix_spans_span_type'), table_name='spans')
    op.drop_index('ix_spans_parent_span_id', table_name='spans')
    op.drop_index('ix_spans_trace_id', table_name='spans')
    op.drop_index(op.f('ix_spans_session_id'), table_name='spans')
    op.drop_index(op.f('ix_spans_id'), table_name='spans')

    # Drop table
    op.drop_table('spans')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS spanstatus')
    op.execute('DROP TYPE IF EXISTS spantype')
