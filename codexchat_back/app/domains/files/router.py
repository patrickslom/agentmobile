from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File as FastAPIFile, Form, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.archive_queries import get_conversation
from app.db.session import get_db
from app.domains.auth.dependencies import get_current_user
from app.domains.files.service import (
    get_active_file,
    get_upload_limit_bytes,
    resolve_default_message_id,
    resolve_file_absolute_path,
    store_uploaded_file,
    validate_message_in_conversation,
)

router = APIRouter(tags=["files"])


class UploadedFileResponse(BaseModel):
    id: str
    conversation_id: str
    message_id: str | None
    original_name: str
    storage_path: str
    download_path: str
    mime_type: str
    size_bytes: int
    created_at: datetime


@router.post(
    "/conversations/{conversation_id}/files",
    status_code=status.HTTP_201_CREATED,
)
def upload_files(
    conversation_id: UUID,
    files: list[UploadFile] = FastAPIFile(...),
    message_id: UUID | None = Form(default=None),
    _=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, list[UploadedFileResponse]]:
    conversation = get_conversation(db, conversation_id, include_archived=False)
    if conversation is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="Conversation not found",
            details={"conversation_id": str(conversation_id)},
        )

    if not files:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="BAD_REQUEST",
            message="At least one file is required",
            details={},
        )

    linked_message_id = message_id
    if linked_message_id is not None:
        validate_message_in_conversation(
            db,
            conversation_id=conversation_id,
            message_id=linked_message_id,
        )
    else:
        linked_message_id = resolve_default_message_id(db, conversation_id=conversation_id)

    max_upload_bytes = get_upload_limit_bytes(db)
    stored = []
    try:
        for upload in files:
            stored.append(
                store_uploaded_file(
                    db,
                    conversation_id=conversation_id,
                    upload=upload,
                    message_id=linked_message_id,
                    max_upload_bytes=max_upload_bytes,
                )
            )
    except Exception:
        db.rollback()
        for item in stored:
            try:
                resolve_file_absolute_path(item.record).unlink(missing_ok=True)
            except Exception:
                continue
        raise

    db.commit()

    return {
        "files": [
            UploadedFileResponse(
                id=str(item.record.id),
                conversation_id=str(item.record.conversation_id),
                message_id=str(item.linked_message_id) if item.linked_message_id else None,
                original_name=item.record.original_name,
                storage_path=item.record.storage_path,
                download_path=f"/api/files/{item.record.id}",
                mime_type=item.record.mime_type,
                size_bytes=item.record.size_bytes,
                created_at=item.record.created_at,
            )
            for item in stored
        ]
    }


@router.get("/files/{file_id}")
def download_file(
    file_id: UUID,
    _=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    file_record = get_active_file(db, file_id=file_id)
    if file_record is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="File not found",
            details={"file_id": str(file_id)},
        )

    conversation = get_conversation(db, file_record.conversation_id, include_archived=False)
    if conversation is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="Conversation not found",
            details={"conversation_id": str(file_record.conversation_id)},
        )

    absolute_path = resolve_file_absolute_path(file_record)
    if not absolute_path.exists():
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="Stored file is missing",
            details={"file_id": str(file_id)},
        )

    return FileResponse(
        path=str(absolute_path),
        media_type=file_record.mime_type,
        filename=file_record.original_name,
        content_disposition_type="inline",
    )
