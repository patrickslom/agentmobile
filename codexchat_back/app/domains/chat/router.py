from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.archive_queries import (
    get_conversation,
    list_conversations,
    list_message_files_for_conversation,
    list_messages_for_conversation,
    search_conversations,
)
from app.db.models import Conversation, File, Message, Settings, User
from app.db.session import get_db
from app.domains.auth.dependencies import get_current_user
from app.domains.warnings import WarningPayload, build_warning_payloads

router = APIRouter(prefix="/conversations", tags=["chat"])

DEFAULT_CONVERSATION_TITLE = "New Conversation"
MAX_TITLE_LENGTH = 255


class ConversationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=MAX_TITLE_LENGTH)


class ConversationRenameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(max_length=MAX_TITLE_LENGTH)


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    metadata_json: dict[str, object]
    files: list["MessageFileResponse"]
    created_at: datetime
    archived_at: datetime | None
    is_archived: bool


class MessageFileResponse(BaseModel):
    id: str
    original_name: str
    storage_path: str
    download_path: str
    mime_type: str
    size_bytes: int
    created_at: datetime
    archived_at: datetime | None
    is_archived: bool


class ConversationResponse(BaseModel):
    id: str
    title: str
    codex_thread_id: str | None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None
    is_archived: bool
    relevance_score: float | None = None


class SearchPaginationResponse(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next_page: bool


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse]


def _normalize_title_or_default(title: str | None) -> str:
    normalized = (title or "").strip()
    if not normalized:
        return DEFAULT_CONVERSATION_TITLE
    return normalized


def _normalize_title_or_error(title: str) -> str:
    normalized = title.strip()
    if not normalized:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="BAD_REQUEST",
            message="Title cannot be empty",
            details={},
        )
    return normalized


def _conversation_to_response(
    conversation: Conversation,
    *,
    relevance_score: float | None = None,
) -> ConversationResponse:
    return ConversationResponse(
        id=str(conversation.id),
        title=conversation.title,
        codex_thread_id=conversation.codex_thread_id,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        archived_at=conversation.archived_at,
        is_archived=conversation.archived_at is not None,
        relevance_score=relevance_score,
    )


def _message_to_response(message: Message, *, attached_files: list[File]) -> MessageResponse:
    return MessageResponse(
        id=str(message.id),
        role=message.role,
        content=message.content,
        metadata_json=message.metadata_json or {},
        files=[
            _file_to_response(file_row)
            for file_row in attached_files
        ],
        created_at=message.created_at,
        archived_at=message.archived_at,
        is_archived=message.archived_at is not None,
    )


def _file_to_response(file_row: File) -> MessageFileResponse:
    return MessageFileResponse(
        id=str(file_row.id),
        original_name=file_row.original_name,
        storage_path=file_row.storage_path,
        download_path=f"/api/files/{file_row.id}",
        mime_type=file_row.mime_type,
        size_bytes=file_row.size_bytes,
        created_at=file_row.created_at,
        archived_at=file_row.archived_at,
        is_archived=file_row.archived_at is not None,
    )


def _warning_payloads(db: Session) -> list[WarningPayload]:
    settings_row = db.get(Settings, 1)
    execution_mode_default = settings_row.execution_mode_default if settings_row else "regular"
    return build_warning_payloads(execution_mode_default=execution_mode_default)


@router.get("")
def get_conversations(
    include_archived: bool = Query(default=False),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    conversations = list_conversations(db, include_archived=include_archived, limit=200)
    return {
        "conversations": [
            _conversation_to_response(conversation) for conversation in conversations
        ],
        "warnings": _warning_payloads(db),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreateRequest,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    conversation = Conversation(title=_normalize_title_or_default(payload.title))
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return {
        "conversation": _conversation_to_response(conversation),
        "warnings": _warning_payloads(db),
    }


@router.get("/search")
def search_conversation_index(
    q: str = Query(min_length=1, max_length=500),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    include_archived: bool = Query(default=False),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    normalized_query = q.strip()
    if not normalized_query:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="BAD_REQUEST",
            message="Search query cannot be empty",
            details={},
        )

    search_results, total = search_conversations(
        db,
        query=normalized_query,
        include_archived=include_archived,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total else 0
    pagination = SearchPaginationResponse(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        has_next_page=page < total_pages,
    )

    return {
        "conversations": [
            _conversation_to_response(conversation, relevance_score=relevance_score)
            for conversation, relevance_score in search_results
        ],
        "pagination": pagination,
        "warnings": _warning_payloads(db),
    }


@router.get("/{conversation_id}")
def get_conversation_detail(
    conversation_id: UUID,
    include_archived: bool = Query(default=False),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    conversation = get_conversation(
        db,
        conversation_id,
        include_archived=include_archived,
    )
    if conversation is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="Conversation not found",
            details={},
        )

    messages = list_messages_for_conversation(
        db,
        conversation_id,
        include_archived=include_archived,
    )
    file_map = list_message_files_for_conversation(
        db,
        conversation_id,
        include_archived=include_archived,
    )

    detail = ConversationDetailResponse(
        **_conversation_to_response(conversation).model_dump(),
        messages=[
            _message_to_response(message, attached_files=file_map.get(message.id, []))
            for message in messages
        ],
    )
    return {
        "conversation": detail,
        "warnings": _warning_payloads(db),
    }


@router.post("/{conversation_id}/title")
def rename_conversation(
    conversation_id: UUID,
    payload: ConversationRenameRequest,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    conversation = get_conversation(db, conversation_id, include_archived=False)
    if conversation is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="Conversation not found",
            details={},
        )

    conversation.title = _normalize_title_or_error(payload.title)
    db.commit()
    db.refresh(conversation)
    return {
        "conversation": _conversation_to_response(conversation),
        "warnings": _warning_payloads(db),
    }
