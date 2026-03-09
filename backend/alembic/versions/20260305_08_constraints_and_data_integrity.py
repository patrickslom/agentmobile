"""Add FK and constraint hardening for data integrity.

Revision ID: 20260305_08
Revises: 20260305_06
Create Date: 2026-03-05 18:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260305_08"
down_revision: str | None = "20260305_06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Core relation FKs with RESTRICT defaults and targeted CASCADEs for dependent tables.
    op.create_foreign_key(
        "fk_messages_conversation_id_conversations",
        "messages",
        "conversations",
        ["conversation_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_files_conversation_id_conversations",
        "files",
        "conversations",
        ["conversation_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_message_files_message_id_messages",
        "message_files",
        "messages",
        ["message_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_message_files_file_id_files",
        "message_files",
        "files",
        ["file_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "fk_sessions_user_id_users",
        "sessions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_settings_updated_by_user_id_users",
        "settings",
        "users",
        ["updated_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_audit_logs_actor_user_id_users",
        "audit_logs",
        "users",
        ["actor_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_audit_logs_target_user_id_users",
        "audit_logs",
        "users",
        ["target_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Adjust existing FKs to match the archive-first delete policy.
    op.drop_constraint(
        "fk_heartbeat_jobs_conversation_id_conversations",
        "heartbeat_jobs",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_heartbeat_jobs_conversation_id_conversations",
        "heartbeat_jobs",
        "conversations",
        ["conversation_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        "fk_conversation_locks_conversation_id_conversations",
        "conversation_locks",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_conversation_locks_conversation_id_conversations",
        "conversation_locks",
        "conversations",
        ["conversation_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # Value constraints.
    op.create_check_constraint(
        "ck_files_size_bytes_non_negative",
        "files",
        condition=sa.text("size_bytes >= 0"),
    )


def downgrade() -> None:
    op.drop_constraint("ck_files_size_bytes_non_negative", "files", type_="check")

    op.drop_constraint(
        "fk_conversation_locks_conversation_id_conversations",
        "conversation_locks",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_conversation_locks_conversation_id_conversations",
        "conversation_locks",
        "conversations",
        ["conversation_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        "fk_heartbeat_jobs_conversation_id_conversations",
        "heartbeat_jobs",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_heartbeat_jobs_conversation_id_conversations",
        "heartbeat_jobs",
        "conversations",
        ["conversation_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("fk_audit_logs_target_user_id_users", "audit_logs", type_="foreignkey")
    op.drop_constraint("fk_audit_logs_actor_user_id_users", "audit_logs", type_="foreignkey")
    op.drop_constraint("fk_settings_updated_by_user_id_users", "settings", type_="foreignkey")
    op.drop_constraint("fk_sessions_user_id_users", "sessions", type_="foreignkey")
    op.drop_constraint("fk_message_files_file_id_files", "message_files", type_="foreignkey")
    op.drop_constraint("fk_message_files_message_id_messages", "message_files", type_="foreignkey")
    op.drop_constraint("fk_files_conversation_id_conversations", "files", type_="foreignkey")
    op.drop_constraint("fk_messages_conversation_id_conversations", "messages", type_="foreignkey")
