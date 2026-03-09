"""Add user-scoped assistant message bookmarks.

Revision ID: 20260308_16
Revises: 20260308_15
Create Date: 2026-03-08 12:15:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260308_16"
down_revision: str | None = "20260308_15"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "message_bookmarks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "message_id", name="uq_message_bookmarks_user_message"),
    )
    op.create_index(
        "ix_message_bookmarks_user_created_at",
        "message_bookmarks",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_message_bookmarks_user_conversation",
        "message_bookmarks",
        ["user_id", "conversation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_message_bookmarks_user_conversation", table_name="message_bookmarks")
    op.drop_index("ix_message_bookmarks_user_created_at", table_name="message_bookmarks")
    op.drop_table("message_bookmarks")
