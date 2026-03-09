"""Add conversation lock schema with stale recovery fields.

Revision ID: 20260305_06
Revises: 20260305_05
Create Date: 2026-03-05 16:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260305_06"
down_revision: str | None = "20260305_05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversation_locks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "resource_type",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'conversation'"),
        ),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("locked_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("owner_token", sa.String(length=128), nullable=False),
        sa.Column(
            "locked_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "last_heartbeat_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "stale_after_seconds",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("120"),
        ),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.CheckConstraint(
            "resource_type = 'conversation'",
            name="ck_conversation_locks_resource_type",
        ),
        sa.CheckConstraint(
            "resource_id = conversation_id",
            name="ck_conversation_locks_resource_matches",
        ),
        sa.CheckConstraint(
            "stale_after_seconds >= 1",
            name="ck_conversation_locks_stale_after_seconds_min",
        ),
        sa.CheckConstraint(
            "expires_at >= locked_at",
            name="ck_conversation_locks_expires_after_locked",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_conversation_locks_conversation_id_conversations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["locked_by"],
            ["users.id"],
            name="fk_conversation_locks_locked_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("conversation_id", name="uq_conversation_locks_conversation_id"),
    )

    op.create_index(
        "ix_conversation_locks_resource_type_resource_id",
        "conversation_locks",
        ["resource_type", "resource_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversation_locks_last_heartbeat_at",
        "conversation_locks",
        ["last_heartbeat_at"],
        unique=False,
    )
    op.create_index(
        "ix_conversation_locks_locked_by",
        "conversation_locks",
        ["locked_by"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_conversation_locks_locked_by", table_name="conversation_locks")
    op.drop_index("ix_conversation_locks_last_heartbeat_at", table_name="conversation_locks")
    op.drop_index(
        "ix_conversation_locks_resource_type_resource_id",
        table_name="conversation_locks",
    )
    op.drop_table("conversation_locks")
