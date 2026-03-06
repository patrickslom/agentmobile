"""Operational maintenance helpers for periodic DB housekeeping."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session


def cleanup_expired_sessions(db: Session) -> int:
    """Delete expired and already-revoked sessions; idempotent."""
    result = db.execute(
        text(
            """
            DELETE FROM sessions
            WHERE expires_at < now()
            """
        )
    )
    db.commit()
    return result.rowcount or 0


def cleanup_stale_locks(db: Session) -> int:
    """Delete stale or expired conversation lock rows; idempotent."""
    result = db.execute(
        text(
            """
            DELETE FROM conversation_locks
            WHERE expires_at < now()
               OR last_heartbeat_at + make_interval(secs => stale_after_seconds) < now()
            """
        )
    )
    db.commit()
    return result.rowcount or 0


def archive_old_messages_and_files(
    db: Session,
    *,
    days_old: int = 90,
) -> dict[str, int]:
    """Soft-archive old messages/files and mark affected conversations archived."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_old)
    message_result = db.execute(
        text(
            """
            UPDATE messages
            SET archived_at = now()
            WHERE archived_at IS NULL
              AND created_at < :cutoff
            """
        ),
        {"cutoff": cutoff},
    )
    file_result = db.execute(
        text(
            """
            UPDATE files
            SET archived_at = now()
            WHERE archived_at IS NULL
              AND created_at < :cutoff
            """
        ),
        {"cutoff": cutoff},
    )
    conversation_result = db.execute(
        text(
            """
            UPDATE conversations c
            SET archived_at = now()
            WHERE c.archived_at IS NULL
              AND EXISTS (
                  SELECT 1
                  FROM messages m
                  WHERE m.conversation_id = c.id
                    AND m.archived_at IS NOT NULL
              )
            """
        )
    )
    db.commit()
    return {
        "messages_archived": message_result.rowcount or 0,
        "files_archived": file_result.rowcount or 0,
        "conversations_archived": conversation_result.rowcount or 0,
    }
