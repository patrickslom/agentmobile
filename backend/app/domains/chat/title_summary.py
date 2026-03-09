from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Conversation, ConversationTitleSummaryJob, Message

DEFAULT_CONVERSATION_TITLE = "New Conversation"
TITLE_SUMMARY_TRIGGER_MESSAGE_COUNT = 4
TITLE_SUMMARY_WINDOW_MESSAGE_LIMIT = 4


def conversation_needs_title_summary(conversation: Conversation) -> bool:
    title_needs_generation = (
        conversation.title_generated_at is None
        and conversation.title.strip() == DEFAULT_CONVERSATION_TITLE
    )
    summary_needs_generation = (
        conversation.summary_generated_at is None
        or not (conversation.summary_short or "").strip()
    )
    return title_needs_generation or summary_needs_generation


def first_window_message_count(db: Session, *, conversation_id: UUID) -> int:
    count = db.execute(
        select(func.count(Message.id))
        .where(
            Message.conversation_id == conversation_id,
            Message.archived_at.is_(None),
            Message.role.in_(("user", "assistant")),
        )
    ).scalar_one()
    return int(count or 0)


def list_first_window_messages(db: Session, *, conversation_id: UUID) -> list[Message]:
    return list(
        db.execute(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.archived_at.is_(None),
                Message.role.in_(("user", "assistant")),
            )
            .order_by(Message.created_at.asc())
            .limit(TITLE_SUMMARY_WINDOW_MESSAGE_LIMIT)
        ).scalars()
    )


def enqueue_title_summary_job_if_ready(db: Session, *, conversation_id: UUID) -> bool:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or conversation.archived_at is not None:
        return False
    if not conversation_needs_title_summary(conversation):
        return False
    if first_window_message_count(db, conversation_id=conversation_id) < TITLE_SUMMARY_TRIGGER_MESSAGE_COUNT:
        return False

    now = datetime.now(tz=UTC)
    job = db.execute(
        select(ConversationTitleSummaryJob).where(
            ConversationTitleSummaryJob.conversation_id == conversation_id
        )
    ).scalar_one_or_none()

    if job is None:
        db.add(
            ConversationTitleSummaryJob(
                conversation_id=conversation_id,
                status="pending",
                available_at=now,
                requested_at=now,
                started_at=None,
                finished_at=None,
                error_text=None,
            )
        )
        db.flush()
        return True

    if job.status in {"pending", "running"}:
        return False

    job.status = "pending"
    job.available_at = now
    job.requested_at = now
    job.started_at = None
    job.finished_at = None
    job.error_text = None
    db.flush()
    return True
