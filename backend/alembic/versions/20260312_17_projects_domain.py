"""Add projects domain and conversation project state.

Revision ID: 20260312_17
Revises: 20260308_16
Create Date: 2026-03-12 22:10:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260312_17"
down_revision: str | None = "20260308_16"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("root_path", sa.String(length=2048), nullable=False),
        sa.Column("index_md_path", sa.String(length=2048), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
        sa.CheckConstraint("char_length(trim(name)) > 0", name="ck_projects_name_not_empty"),
        sa.CheckConstraint("char_length(trim(root_path)) > 0", name="ck_projects_root_path_not_empty"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_projects_name"),
        sa.UniqueConstraint("root_path", name="uq_projects_root_path"),
    )
    op.create_index("ix_projects_is_active_updated_at", "projects", ["is_active", "updated_at"], unique=False)

    op.add_column(
        "conversations",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column(
            "project_mode",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'unknown'"),
        ),
    )
    op.add_column(
        "conversations",
        sa.Column(
            "project_clarification_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_foreign_key(
        "fk_conversations_project_id_projects",
        "conversations",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_conversations_project_mode",
        "conversations",
        "project_mode IN ('unknown', 'general', 'project_bound')",
    )
    op.create_index("ix_conversations_project_id", "conversations", ["project_id"], unique=False)

    op.execute(
        """
        CREATE TRIGGER trg_projects_set_updated_at
        BEFORE UPDATE ON projects
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_projects_set_updated_at ON projects")
    op.drop_index("ix_conversations_project_id", table_name="conversations")
    op.drop_constraint("ck_conversations_project_mode", "conversations", type_="check")
    op.drop_constraint("fk_conversations_project_id_projects", "conversations", type_="foreignkey")
    op.drop_column("conversations", "project_clarification_json")
    op.drop_column("conversations", "project_mode")
    op.drop_column("conversations", "project_id")

    op.drop_index("ix_projects_is_active_updated_at", table_name="projects")
    op.drop_table("projects")
