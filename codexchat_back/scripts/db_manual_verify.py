"""Manual DB verification checks for TODO section 12."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.archive_queries import (
    archive_conversation,
    list_conversations,
    list_messages_for_conversation,
    restore_conversation,
)
from app.db.models import Conversation, ConversationLock, HeartbeatJob, HeartbeatRun, HeartbeatSchedule, Message
from app.db.session import SessionLocal


def main() -> int:
    checks: dict[str, bool] = {}
    created_ids: dict[str, str] = {}
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        conversation = Conversation(title=f"verify-{uuid4()}", codex_thread_id=f"thread-{uuid4()}")
        db.add(conversation)
        db.flush()
        created_ids["conversation_id"] = str(conversation.id)

        message = Message(conversation_id=conversation.id, role="user", content="hello")
        db.add(message)
        db.flush()

        heartbeat_job = HeartbeatJob(
            conversation_id=conversation.id,
            instruction_file_path="/workspace/heartbeat.md",
            enabled=True,
        )
        db.add(heartbeat_job)
        db.flush()

        heartbeat_schedule = HeartbeatSchedule(
            heartbeat_job_id=heartbeat_job.id,
            interval_minutes=5,
            next_run_at=now + timedelta(minutes=5),
        )
        heartbeat_run = HeartbeatRun(
            heartbeat_job_id=heartbeat_job.id,
            status="queued",
        )
        db.add_all([heartbeat_schedule, heartbeat_run])
        db.commit()

        checks["heartbeat_tables_populate"] = True

        archive_conversation(db, conversation.id, cascade_children=True)
        db.commit()
        default_list = list_conversations(db)
        archived_list = list_conversations(db, include_archived=True)
        archived_messages = list_messages_for_conversation(db, conversation.id)
        checks["archived_hidden_by_default"] = (
            conversation.id not in {row.id for row in default_list}
            and conversation.id in {row.id for row in archived_list}
            and len(archived_messages) == 0
        )

        restore_conversation(db, conversation.id, restore_children=True)
        db.commit()
        restored_messages = list_messages_for_conversation(db, conversation.id)
        checks["archive_restore_flow"] = len(restored_messages) == 1

        expires_at = now + timedelta(seconds=60)
        lock_one = ConversationLock(
            conversation_id=conversation.id,
            resource_id=conversation.id,
            owner_token=f"tok-{uuid4()}",
            expires_at=expires_at,
        )
        db.add(lock_one)
        db.commit()

        lock_two = ConversationLock(
            conversation_id=conversation.id,
            resource_id=conversation.id,
            owner_token=f"tok-{uuid4()}",
            expires_at=expires_at,
        )
        db.add(lock_two)
        try:
            db.commit()
            checks["lock_concurrency_protection"] = False
        except IntegrityError:
            db.rollback()
            checks["lock_concurrency_protection"] = True

        index_rows = db.execute(
            text(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname IN ('ix_conversations_title_tsv', 'ix_messages_content_tsv')
                """
            )
        ).fetchall()
        found_indexes = {row[0] for row in index_rows}

        db.execute(text("SET LOCAL enable_seqscan = off"))
        explain_rows = db.execute(
            text(
                """
                EXPLAIN SELECT id
                FROM conversations
                WHERE to_tsvector('simple', coalesce(title, '')) @@ plainto_tsquery('simple', 'verify')
                """
            )
        ).fetchall()
        explain_text = " ".join(row[0] for row in explain_rows)
        checks["search_indexes_exist_and_used"] = (
            found_indexes == {"ix_conversations_title_tsv", "ix_messages_content_tsv"}
            and "Index" in explain_text
        )

        db.execute(text("DELETE FROM conversation_locks WHERE conversation_id = :cid"), {"cid": conversation.id})
        db.execute(text("DELETE FROM heartbeat_runs WHERE heartbeat_job_id = :jid"), {"jid": heartbeat_job.id})
        db.execute(
            text("DELETE FROM heartbeat_schedules WHERE heartbeat_job_id = :jid"),
            {"jid": heartbeat_job.id},
        )
        db.execute(text("DELETE FROM heartbeat_jobs WHERE id = :jid"), {"jid": heartbeat_job.id})
        db.execute(text("DELETE FROM messages WHERE id = :mid"), {"mid": message.id})
        db.execute(text("DELETE FROM conversations WHERE id = :cid"), {"cid": conversation.id})
        db.commit()

    success = all(checks.values())
    print(json.dumps({"ok": success, "checks": checks, "created_ids": created_ids}, sort_keys=True))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
