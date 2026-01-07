"""add_media_attachments

Revision ID: b2c3d4e5f6a7
Revises: 6ca0e7b3ec95
Create Date: 2026-01-07 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = '6ca0e7b3ec95'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create session_media_files table
    op.create_table('session_media_files',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=True),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('media_type', sa.String(20), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('url', sa.String(500), nullable=False),
        sa.Column('file_metadata', sa.JSON(), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_session_media_files_id'), 'session_media_files', ['id'], unique=False)
    op.create_index(op.f('ix_session_media_files_session_id'), 'session_media_files', ['session_id'], unique=False)
    op.create_index(op.f('ix_session_media_files_media_type'), 'session_media_files', ['media_type'], unique=False)

    # Add content_blocks column to messages table
    op.add_column('messages', sa.Column('content_blocks', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove content_blocks column from messages
    op.drop_column('messages', 'content_blocks')

    # Drop session_media_files table and indexes
    op.drop_index(op.f('ix_session_media_files_media_type'), table_name='session_media_files')
    op.drop_index(op.f('ix_session_media_files_session_id'), table_name='session_media_files')
    op.drop_index(op.f('ix_session_media_files_id'), table_name='session_media_files')
    op.drop_table('session_media_files')
