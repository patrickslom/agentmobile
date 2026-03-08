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
    author_user_id: str | None = None
    author_display_name: str | None = None
    author_profile_picture_url: str | None = None
    is_current_user_author: bool | None = None
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


def _normalize_author_display_name(raw_value: object) -> str | None:
    if not isinstance(raw_value, str):
        return None
    normalized = raw_value.strip()
    if not normalized:
        return None
    return normalized


def _message_author_identity(
    message: Message,
    *,
    current_user: User | None,
) -> tuple[str | None, str | None, str | None, bool | None]:
    if message.role != "user":
        return (None, None, None, None)

    metadata = message.metadata_json or {}
    author_user_id = metadata.get("author_user_id")
    if not isinstance(author_user_id, str) and message.user_id is not None:
        author_user_id = str(message.user_id)
    elif not isinstance(author_user_id, str):
        author_user_id = None

    author_display_name = _normalize_author_display_name(metadata.get("author_display_name"))
    if author_display_name is None:
        author_display_name = "Former User"

    author_profile_picture_url = (
        metadata.get("author_profile_picture_url")
        if isinstance(metadata.get("author_profile_picture_url"), str)
        else None
    )

    is_current_user_author: bool | None = None
    if current_user is not None and message.user_id is not None:
        is_current_user_author = current_user.id == message.user_id

    return (
        author_user_id,
        author_display_name,
        author_profile_picture_url,
        is_current_user_author,
    )


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


def _message_to_response(
    message: Message,
    *,
    attached_files: list[File],
    current_user: User | None,
) -> MessageResponse:
    author_user_id, author_display_name, author_profile_picture_url, is_current_user_author = (
        _message_author_identity(message, current_user=current_user)
    )

    return MessageResponse(
        id=str(message.id),
        role=message.role,
        content=message.content,
        author_user_id=author_user_id,
        author_display_name=author_display_name,
        author_profile_picture_url=author_profile_picture_url,
        is_current_user_author=is_current_user_author,
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
    current_user: User = Depends(get_current_user),
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
            _message_to_response(
                message,
                attached_files=file_map.get(message.id, []),
                current_user=current_user,
            )
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
