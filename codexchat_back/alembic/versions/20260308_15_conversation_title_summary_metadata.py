"""Add conversation title summary metadata and background job queue.

Revision ID: 20260308_15
Revises: 20260307_14
Create Date: 2026-03-08 10:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260308_15"
down_revision: str | None = "20260307_14"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("summary_short", sa.String(length=255), nullable=True))
    op.add_column(
        "conversations",
        sa.Column("title_generated_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("summary_generated_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
    )

    op.create_table(
        "conversation_title_summary_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "available_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "requested_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("started_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("finished_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_conversation_title_summary_jobs_status",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_conversation_title_summary_jobs_attempt_count_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_cts_jobs_conversation_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("conversation_id", name="uq_conversation_title_summary_jobs_conversation_id"),
    )
    op.create_index(
        "ix_conversation_title_summary_jobs_available_at",
        "conversation_title_summary_jobs",
        ["available_at"],
        unique=False,
    )
    op.execute(
        """
        CREATE TRIGGER trg_conversation_title_summary_jobs_set_updated_at
        BEFORE UPDATE ON conversation_title_summary_jobs
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_conversation_title_summary_jobs_set_updated_at ON conversation_title_summary_jobs"
    )
    op.drop_index(
        "ix_conversation_title_summary_jobs_available_at",
        table_name="conversation_title_summary_jobs",
    )
    op.drop_table("conversation_title_summary_jobs")

    op.drop_column("conversations", "summary_generated_at")
    op.drop_column("conversations", "title_generated_at")
    op.drop_column("conversations", "summary_short")
