"""Archive-aware query helpers for archivable tables.

Default behavior is active-only (`archived_at IS NULL`).
Admin/archive flows may opt-in to include archived rows explicitly.
"""

from __future__ import annotations

import uuid
from typing import TypeVar

from sqlalchemy import Select, func, select, update
from sqlalchemy.orm import Session

from app.db.models import Conversation, File, HeartbeatJob, Message

ArchivableModel = TypeVar(
    "ArchivableModel",
    Conversation,
    Message,
    File,
    HeartbeatJob,
)


def apply_archive_scope(
    stmt: Select[tuple[ArchivableModel]],
    model: type[ArchivableModel],
    *,
    include_archived: bool = False,
    only_archived: bool = False,
) -> Select[tuple[ArchivableModel]]:
    """Apply standardized soft-delete filtering semantics to a SELECT statement."""
    if only_archived:
        return stmt.where(model.archived_at.is_not(None))
    if include_archived:
        return stmt
    return stmt.where(model.archived_at.is_(None))


def list_conversations(
    db: Session,
    *,
    include_archived: bool = False,
    only_archived: bool = False,
    limit: int = 100,
) -> list[Conversation]:
    stmt = select(Conversation).order_by(Conversation.updated_at.desc()).limit(limit)
    scoped = apply_archive_scope(
        stmt,
        Conversation,
        include_archived=include_archived,
        only_archived=only_archived,
    )
    return list(db.execute(scoped).scalars())


def get_conversation(
    db: Session,
    conversation_id: uuid.UUID,
    *,
    include_archived: bool = False,
) -> Conversation | None:
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    scoped = apply_archive_scope(stmt, Conversation, include_archived=include_archived)
    return db.execute(scoped).scalar_one_or_none()


def list_messages_for_conversation(
    db: Session,
    conversation_id: uuid.UUID,
    *,
    include_archived: bool = False,
    only_archived: bool = False,
) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    scoped = apply_archive_scope(
        stmt,
        Message,
        include_archived=include_archived,
        only_archived=only_archived,
    )
    return list(db.execute(scoped).scalars())


def list_files_for_conversation(
    db: Session,
    conversation_id: uuid.UUID,
    *,
    include_archived: bool = False,
    only_archived: bool = False,
) -> list[File]:
    stmt = (
        select(File)
        .where(File.conversation_id == conversation_id)
        .order_by(File.created_at.asc())
    )
    scoped = apply_archive_scope(
        stmt,
        File,
        include_archived=include_archived,
        only_archived=only_archived,
    )
    return list(db.execute(scoped).scalars())


def list_heartbeat_jobs_for_conversation(
    db: Session,
    conversation_id: uuid.UUID,
    *,
    include_archived: bool = False,
    only_archived: bool = False,
) -> list[HeartbeatJob]:
    stmt = (
        select(HeartbeatJob)
        .where(HeartbeatJob.conversation_id == conversation_id)
        .order_by(HeartbeatJob.created_at.asc())
    )
    scoped = apply_archive_scope(
        stmt,
        HeartbeatJob,
        include_archived=include_archived,
        only_archived=only_archived,
    )
    return list(db.execute(scoped).scalars())


def list_archived_conversations(db: Session, *, limit: int = 100) -> list[Conversation]:
    """Admin/archive helper: return archived conversations explicitly."""
    return list_conversations(db, only_archived=True, limit=limit)


def archive_conversation(
    db: Session,
    conversation_id: uuid.UUID,
    *,
    cascade_children: bool = True,
) -> None:
    """Soft-delete a conversation and optionally its dependent archive-aware rows."""
    db.execute(
        update(Conversation)
        .where(Conversation.id == conversation_id, Conversation.archived_at.is_(None))
        .values(archived_at=func.now())
    )
    if cascade_children:
        db.execute(
            update(Message)
            .where(Message.conversation_id == conversation_id, Message.archived_at.is_(None))
            .values(archived_at=func.now())
        )
        db.execute(
            update(File)
            .where(File.conversation_id == conversation_id, File.archived_at.is_(None))
            .values(archived_at=func.now())
        )
        db.execute(
            update(HeartbeatJob)
            .where(
                HeartbeatJob.conversation_id == conversation_id,
                HeartbeatJob.archived_at.is_(None),
            )
            .values(archived_at=func.now())
        )


def restore_conversation(
    db: Session,
    conversation_id: uuid.UUID,
    *,
    restore_children: bool = True,
) -> None:
    """Restore a soft-deleted conversation and optionally child rows."""
    db.execute(
        update(Conversation)
        .where(Conversation.id == conversation_id, Conversation.archived_at.is_not(None))
        .values(archived_at=None)
    )
    if restore_children:
        db.execute(
            update(Message)
            .where(Message.conversation_id == conversation_id, Message.archived_at.is_not(None))
            .values(archived_at=None)
        )
        db.execute(
            update(File)
            .where(File.conversation_id == conversation_id, File.archived_at.is_not(None))
            .values(archived_at=None)
        )
        db.execute(
            update(HeartbeatJob)
            .where(
                HeartbeatJob.conversation_id == conversation_id,
                HeartbeatJob.archived_at.is_not(None),
            )
            .values(archived_at=None)
        )
