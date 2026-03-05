"""Add settings and audit log tables.

Revision ID: 20260305_04
Revises: 20260305_03
Create Date: 2026-03-05 15:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260305_04"
down_revision: str | None = "20260305_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "settings",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "execution_mode_default",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'regular'"),
        ),
        sa.Column(
            "upload_limit_mb_default",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("15"),
        ),
        sa.Column(
            "heartbeat_enabled_default",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "heartbeat_cap_default",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("10"),
        ),
        sa.Column(
            "heartbeat_unlimited_default",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "theme_default",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'light'"),
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint("id = 1", name="ck_settings_single_row"),
        sa.CheckConstraint(
            "execution_mode_default IN ('regular', 'yolo')",
            name="ck_settings_execution_mode_default",
        ),
        sa.CheckConstraint(
            "upload_limit_mb_default >= 1",
            name="ck_settings_upload_limit_mb_default_min",
        ),
        sa.CheckConstraint(
            "heartbeat_cap_default >= 1",
            name="ck_settings_heartbeat_cap_default_min",
        ),
        sa.CheckConstraint("theme_default IN ('light', 'dark')", name="ck_settings_theme_default"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """
        CREATE TRIGGER trg_settings_set_updated_at
        BEFORE UPDATE ON settings
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at()
        """
    )

    op.create_table(
        "audit_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("request_id", sa.Text(), nullable=True),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"], unique=False)
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.execute("DROP TRIGGER IF EXISTS trg_settings_set_updated_at ON settings")
    op.drop_table("settings")
