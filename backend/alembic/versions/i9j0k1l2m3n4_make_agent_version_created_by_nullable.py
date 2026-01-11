"""make agent_version created_by nullable

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2026-01-11 04:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'i9j0k1l2m3n4'
down_revision: Union[str, None] = 'h8i9j0k1l2m3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make created_by nullable to support built-in agents (which have no creator)
    op.alter_column('agent_versions', 'created_by',
               existing_type=sa.INTEGER(),
               nullable=True)


def downgrade() -> None:
    # Revert to non-nullable (will fail if NULL values exist)
    op.alter_column('agent_versions', 'created_by',
               existing_type=sa.INTEGER(),
               nullable=False)
