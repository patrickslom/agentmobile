"""Archive-aware query helpers for archivable tables.

Default behavior is active-only (`archived_at IS NULL`).
Admin/archive flows may opt-in to include archived rows explicitly.
"""

from __future__ import annotations

import uuid
from typing import TypeVar

from sqlalchemy import Select, and_, cast, desc, func, or_, select, update
from sqlalchemy.sql.sqltypes import Float
from sqlalchemy.orm import Session

from app.db.models import Conversation, File, HeartbeatJob, Message, MessageFile

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


def list_message_files_for_conversation(
    db: Session,
    conversation_id: uuid.UUID,
    *,
    include_archived: bool = False,
) -> dict[uuid.UUID | None, list[File]]:
    stmt = (
        select(MessageFile.message_id, File)
        .join(File, File.id == MessageFile.file_id)
        .where(File.conversation_id == conversation_id)
        .order_by(File.created_at.asc())
    )
    if not include_archived:
        stmt = stmt.where(File.archived_at.is_(None))

    file_map: dict[uuid.UUID | None, list[File]] = {}
    for message_id, file_row in db.execute(stmt):
        file_map.setdefault(message_id, []).append(file_row)
    return file_map


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


def search_conversations(
    db: Session,
    *,
    query: str,
    include_archived: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[tuple[Conversation, float]], int]:
    normalized_query = query.strip()
    if not normalized_query:
        return ([], 0)

    ts_query = func.websearch_to_tsquery("simple", normalized_query)
    title_tsv = func.to_tsvector("simple", func.coalesce(Conversation.title, ""))
    message_tsv = func.to_tsvector("simple", func.coalesce(Message.content, ""))

    join_filters = [Message.conversation_id == Conversation.id]
    if not include_archived:
        join_filters.append(Message.archived_at.is_(None))

    search_filters = [
        or_(
            title_tsv.op("@@")(ts_query),
            message_tsv.op("@@")(ts_query),
        )
    ]
    if not include_archived:
        search_filters.append(Conversation.archived_at.is_(None))

    title_rank = func.ts_rank_cd(title_tsv, ts_query)
    message_rank = func.ts_rank_cd(message_tsv, ts_query)
    relevance_score = func.greatest(
        cast(func.max(title_rank), Float),
        cast(func.coalesce(func.max(message_rank), 0.0), Float),
    ).label("relevance_score")

    offset = (page - 1) * page_size
    search_stmt = (
        select(Conversation, relevance_score)
        .outerjoin(Message, and_(*join_filters))
        .where(*search_filters)
        .group_by(Conversation.id)
        .order_by(desc("relevance_score"), Conversation.updated_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    rows = list(db.execute(search_stmt).all())
    results = [(conversation, float(score or 0.0)) for conversation, score in rows]

    count_stmt = (
        select(func.count(func.distinct(Conversation.id)))
        .select_from(Conversation)
        .outerjoin(Message, and_(*join_filters))
        .where(*search_filters)
    )
    total = int(db.execute(count_stmt).scalar_one() or 0)
    return (results, total)


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
