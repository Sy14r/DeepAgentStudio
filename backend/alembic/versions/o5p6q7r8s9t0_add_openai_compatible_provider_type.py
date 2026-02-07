"""add_openai_compatible_provider_type

Revision ID: o5p6q7r8s9t0
Revises: n4o5p6q7r8s9
Create Date: 2026-02-07

"""
from typing import Sequence, Union
from alembic import op

revision: str = 'o5p6q7r8s9t0'
down_revision: Union[str, None] = 'n4o5p6q7r8s9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE llmprovidertype ADD VALUE IF NOT EXISTS 'OPENAI_COMPATIBLE'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values
    # The value will remain but be unused after downgrade
    pass
