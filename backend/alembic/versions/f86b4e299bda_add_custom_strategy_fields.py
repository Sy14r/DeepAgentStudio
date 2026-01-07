"""add_custom_strategy_fields

Revision ID: f86b4e299bda
Revises: f9a2c8e73d41
Create Date: 2026-01-06 21:01:59.522757

Adds support for custom execution strategies:
- strategy_type: Distinguishes between builtin execution strategies and custom code
- custom_strategy_code: Python code for custom strategies
- code_template_version: Version tracking for code template migrations
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f86b4e299bda'
down_revision: Union[str, None] = 'f9a2c8e73d41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the strategytype enum
    strategytype_enum = postgresql.ENUM('builtin', 'custom_code', name='strategytype', create_type=False)
    strategytype_enum.create(op.get_bind(), checkfirst=True)

    # Add new columns to agent_type_configs
    op.add_column(
        'agent_type_configs',
        sa.Column(
            'strategy_type',
            strategytype_enum,
            server_default='builtin',
            nullable=False
        )
    )
    op.add_column(
        'agent_type_configs',
        sa.Column('custom_strategy_code', sa.Text(), nullable=True)
    )
    op.add_column(
        'agent_type_configs',
        sa.Column(
            'code_template_version',
            sa.Integer(),
            server_default='1',
            nullable=False
        )
    )


def downgrade() -> None:
    # Remove columns
    op.drop_column('agent_type_configs', 'code_template_version')
    op.drop_column('agent_type_configs', 'custom_strategy_code')
    op.drop_column('agent_type_configs', 'strategy_type')

    # Drop the enum type
    strategytype_enum = postgresql.ENUM('builtin', 'custom_code', name='strategytype', create_type=False)
    strategytype_enum.drop(op.get_bind(), checkfirst=True)
