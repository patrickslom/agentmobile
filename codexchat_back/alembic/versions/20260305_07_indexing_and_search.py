"""Add indexing and text search indexes for conversations and related tables.

Revision ID: 20260305_07
Revises: 20260305_06
Create Date: 2026-03-05 17:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260305_07"
down_revision: str | None = "20260305_06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_conversations_updated_at",
        "conversations",
        ["updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_messages_conversation_id_created_at",
        "messages",
        ["conversation_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_files_conversation_id_created_at",
        "files",
        ["conversation_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_conversation_locks_expires_at",
        "conversation_locks",
        ["expires_at"],
        unique=False,
    )

    op.create_index(
        "ix_conversations_title_tsv",
        "conversations",
        [sa.text("to_tsvector('simple', coalesce(title, ''))")],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_messages_content_tsv",
        "messages",
        [sa.text("to_tsvector('simple', coalesce(content, ''))")],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_messages_content_tsv", table_name="messages")
    op.drop_index("ix_conversations_title_tsv", table_name="conversations")
    op.drop_index("ix_conversation_locks_expires_at", table_name="conversation_locks")
    op.drop_index("ix_files_conversation_id_created_at", table_name="files")
    op.drop_index("ix_messages_conversation_id_created_at", table_name="messages")
    op.drop_index("ix_conversations_updated_at", table_name="conversations")
