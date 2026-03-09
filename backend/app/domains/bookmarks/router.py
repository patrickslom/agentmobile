from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import Conversation, Message, MessageBookmark, User
from app.db.session import get_db
from app.domains.auth.dependencies import get_current_user

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])

MAX_NOTE_LENGTH = 2000
MAX_PREVIEW_LENGTH = 240


class BookmarkCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message_id: UUID
    note: str | None = Field(default=None, max_length=MAX_NOTE_LENGTH)


class BookmarkResponse(BaseModel):
    id: str
    user_id: str
    message_id: str
    conversation_id: str
    note: str | None
    created_at: datetime


class BookmarkListItemResponse(BaseModel):
    id: str
    user_id: str
    owner_display_name: str
    owner_profile_picture_url: str | None = None
    is_current_user_owner: bool
    message_id: str
    conversation_id: str
    conversation_title: str
    conversation_summary_short: str | None = None
    message_preview: str
    message_created_at: datetime
    created_at: datetime
    note: str | None = None


def _normalize_note(note: str | None) -> str | None:
    if note is None:
        return None
    normalized = note.strip()
    return normalized or None


def _message_preview(content: str) -> str:
    normalized = re.sub(r"\s+", " ", content).strip()
    if len(normalized) <= MAX_PREVIEW_LENGTH:
        return normalized
    return f"{normalized[: MAX_PREVIEW_LENGTH - 1].rstrip()}…"


def _bookmark_to_response(bookmark: MessageBookmark) -> BookmarkResponse:
    return BookmarkResponse(
        id=str(bookmark.id),
        user_id=str(bookmark.user_id),
        message_id=str(bookmark.message_id),
        conversation_id=str(bookmark.conversation_id),
        note=bookmark.note,
        created_at=bookmark.created_at,
    )


@router.get("")
def list_bookmarks(
    scope: str = Query(default="mine"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, list[BookmarkListItemResponse]]:
    normalized_scope = scope.strip().lower()
    if normalized_scope not in {"mine", "all"}:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="BAD_REQUEST",
            message="Unsupported bookmark scope",
            details={"scope": scope, "allowed": ["mine", "all"]},
        )

    stmt = (
        select(MessageBookmark, Message, Conversation, User)
        .join(Message, Message.id == MessageBookmark.message_id)
        .join(Conversation, Conversation.id == MessageBookmark.conversation_id)
        .join(User, User.id == MessageBookmark.user_id)
        .where(
            Message.archived_at.is_(None),
            Conversation.archived_at.is_(None),
        )
        .order_by(MessageBookmark.created_at.desc())
    )
    if normalized_scope == "mine":
        stmt = stmt.where(MessageBookmark.user_id == current_user.id)
    rows = db.execute(stmt).all()

    return {
        "bookmarks": [
            BookmarkListItemResponse(
                id=str(bookmark.id),
                user_id=str(owner.id),
                owner_display_name=owner.display_name,
                owner_profile_picture_url=owner.profile_picture_url,
                is_current_user_owner=owner.id == current_user.id,
                message_id=str(message.id),
                conversation_id=str(conversation.id),
                conversation_title=conversation.title,
                conversation_summary_short=conversation.summary_short,
                message_preview=_message_preview(message.content),
                message_created_at=message.created_at,
                created_at=bookmark.created_at,
                note=bookmark.note,
            )
            for bookmark, message, conversation, owner in rows
        ]
    }


@router.post("")
def create_bookmark(
    payload: BookmarkCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    message = db.execute(
        select(Message, Conversation)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(
            Message.id == payload.message_id,
            Message.role == "assistant",
            Message.archived_at.is_(None),
            Conversation.archived_at.is_(None),
        )
    ).one_or_none()
    if message is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="Assistant message not found",
            details={"message_id": str(payload.message_id)},
        )

    existing = db.execute(
        select(MessageBookmark).where(
            MessageBookmark.user_id == current_user.id,
            MessageBookmark.message_id == payload.message_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return {"bookmark": _bookmark_to_response(existing), "created": False}

    message_row, conversation = message
    bookmark = MessageBookmark(
        user_id=current_user.id,
        message_id=message_row.id,
        conversation_id=conversation.id,
        note=_normalize_note(payload.note),
    )
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)
    return {"bookmark": _bookmark_to_response(bookmark), "created": True}


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bookmark(
    message_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    bookmark = db.execute(
        select(MessageBookmark).where(
            MessageBookmark.user_id == current_user.id,
            MessageBookmark.message_id == message_id,
        )
    ).scalar_one_or_none()
    if bookmark is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="Bookmark not found",
            details={"message_id": str(message_id)},
        )

    db.delete(bookmark)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
