"""Add user identity snapshot fields for messages."""

from __future__ import annotations

import json
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260307_14"
down_revision: str | None = "20260306_13"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _normalize_display_name_from_email(email: str) -> str:
    local_part = email.split("@", 1)[0].strip().lower()
    normalized = "".join(
        ch for ch in local_part if ch.isalnum() or ch in {"_", "-", "."}
    )
    if not normalized:
        normalized = "user"
    if len(normalized) > 64:
        normalized = normalized[:64]
    return normalized


def _next_available_display_name(base_name: str, used_names: set[str]) -> str:
    candidate = base_name
    suffix = 2
    while candidate in used_names:
        candidate = f"{base_name}-{suffix}"
        if len(candidate) > 64:
            candidate = candidate[:64]
            if "-" in candidate:
                candidate = candidate.rsplit("-", 1)[0]
                if not candidate:
                    candidate = "user"
        suffix += 1
    return candidate


def upgrade() -> None:
    op.add_column("users", sa.Column("display_name", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("profile_picture_url", sa.String(2048), nullable=True))
    op.add_column(
        "messages",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    connection = op.get_bind()
    users = connection.execute(
        text("SELECT id, email, display_name FROM users ORDER BY created_at ASC, id ASC")
    ).mappings().all()

    used_display_names: set[str] = set()
    for row in users:
        existing_name = row["display_name"] if isinstance(row["display_name"], str) else None
        if existing_name:
            normalized_name = existing_name.strip()
        else:
            normalized_name = _next_available_display_name(
                _normalize_display_name_from_email(row["email"]),
                used_display_names,
            )

        if not normalized_name:
            normalized_name = _next_available_display_name("user", used_display_names)

        normalized_name = normalized_name[:64]
        if not normalized_name:
            normalized_name = "user"

        if normalized_name in used_display_names:
            normalized_name = _next_available_display_name(normalized_name, used_display_names)

        used_display_names.add(normalized_name)
        connection.execute(
            text("UPDATE users SET display_name = :display_name WHERE id = :user_id"),
            {
                "display_name": normalized_name,
                "user_id": row["id"],
            },
        )

    op.create_check_constraint(
        "ck_users_display_name_not_empty",
        "users",
        "char_length(trim(display_name)) > 0",
    )
    op.create_unique_constraint("uq_users_display_name", "users", ["display_name"])
    op.alter_column("users", "display_name", nullable=False)

    op.create_index("ix_messages_user_id", "messages", ["user_id"], unique=False)
    op.create_foreign_key(
        "fk_messages_user_id_users",
        "messages",
        "users",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    user_messages = connection.execute(
        text("SELECT id, user_id, metadata_json FROM messages WHERE role = 'user'")
    ).mappings().all()

    for row in user_messages:
        user_id = row["user_id"]
        if user_id is None:
            continue

        user_row = connection.execute(
            text("SELECT display_name, profile_picture_url FROM users WHERE id = :user_id"),
            {"user_id": user_id},
        ).mappings().first()
        if user_row is None:
            continue

        metadata = row["metadata_json"]
        if not isinstance(metadata, dict):
            metadata = {}

        next_metadata = dict(metadata)

        if not isinstance(next_metadata.get("author_user_id"), str):
            next_metadata["author_user_id"] = str(user_id)

        raw_author_name = next_metadata.get("author_display_name")
        if not isinstance(raw_author_name, str):
            next_metadata["author_display_name"] = user_row["display_name"]

        if next_metadata.get("author_display_name") in {"", None}:
            next_metadata["author_display_name"] = "Former User"

        if "author_profile_picture_url" not in next_metadata:
            next_metadata["author_profile_picture_url"] = user_row["profile_picture_url"]

        if next_metadata == metadata:
            continue

        connection.execute(
            text("UPDATE messages SET metadata_json = :metadata_json WHERE id = :message_id"),
            {
                "metadata_json": json.dumps(next_metadata),
                "message_id": row["id"],
            },
        )


def downgrade() -> None:
    op.drop_constraint("fk_messages_user_id_users", "messages", type_="foreignkey")
    op.drop_index("ix_messages_user_id", table_name="messages")
    op.drop_column("messages", "user_id")

    op.drop_constraint("uq_users_display_name", "users", type_="unique")
    op.drop_constraint("ck_users_display_name_not_empty", "users", type_="check")
    op.drop_column("users", "profile_picture_url")
    op.drop_column("users", "display_name")
