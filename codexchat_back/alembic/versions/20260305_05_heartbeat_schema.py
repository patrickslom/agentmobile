"""Add heartbeat schema tables.

Revision ID: 20260305_05
Revises: 20260305_04
Create Date: 2026-03-05 15:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260305_05"
down_revision: str | None = "20260305_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "heartbeat_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instruction_file_path", sa.String(length=2048), nullable=False),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
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
        sa.Column("archived_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_heartbeat_jobs_conversation_id_conversations",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_heartbeat_jobs_conversation_id",
        "heartbeat_jobs",
        ["conversation_id"],
        unique=False,
    )
    op.execute(
        """
        CREATE TRIGGER trg_heartbeat_jobs_set_updated_at
        BEFORE UPDATE ON heartbeat_jobs
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at()
        """
    )

    op.create_table(
        "heartbeat_schedules",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("heartbeat_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("interval_minutes", sa.Integer(), nullable=False),
        sa.Column("next_run_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_run_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
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
            "interval_minutes >= 1",
            name="ck_heartbeat_schedules_interval_minutes_min",
        ),
        sa.ForeignKeyConstraint(
            ["heartbeat_job_id"],
            ["heartbeat_jobs.id"],
            name="fk_heartbeat_schedules_heartbeat_job_id_heartbeat_jobs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_heartbeat_schedules_heartbeat_job_id",
        "heartbeat_schedules",
        ["heartbeat_job_id"],
        unique=False,
    )
    op.execute(
        """
        CREATE TRIGGER trg_heartbeat_schedules_set_updated_at
        BEFORE UPDATE ON heartbeat_schedules
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at()
        """
    )

    op.create_table(
        "heartbeat_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("heartbeat_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'queued'"),
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
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')",
            name="ck_heartbeat_runs_status",
        ),
        sa.ForeignKeyConstraint(
            ["heartbeat_job_id"],
            ["heartbeat_jobs.id"],
            name="fk_heartbeat_runs_heartbeat_job_id_heartbeat_jobs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_heartbeat_runs_heartbeat_job_id",
        "heartbeat_runs",
        ["heartbeat_job_id"],
        unique=False,
    )
    op.create_index("ix_heartbeat_runs_created_at", "heartbeat_runs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_heartbeat_runs_created_at", table_name="heartbeat_runs")
    op.drop_index("ix_heartbeat_runs_heartbeat_job_id", table_name="heartbeat_runs")
    op.drop_table("heartbeat_runs")

    op.execute("DROP TRIGGER IF EXISTS trg_heartbeat_schedules_set_updated_at ON heartbeat_schedules")
    op.drop_index("ix_heartbeat_schedules_heartbeat_job_id", table_name="heartbeat_schedules")
    op.drop_table("heartbeat_schedules")

    op.execute("DROP TRIGGER IF EXISTS trg_heartbeat_jobs_set_updated_at ON heartbeat_jobs")
    op.drop_index("ix_heartbeat_jobs_conversation_id", table_name="heartbeat_jobs")
    op.drop_table("heartbeat_jobs")
