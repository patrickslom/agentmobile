from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.models import File, Message, MessageFile, Settings

DEFAULT_UPLOAD_LIMIT_MB = 15
_FILENAME_SANITIZE_PATTERN = re.compile(r"[^A-Za-z0-9._-]")
_CHUNK_SIZE_BYTES = 1024 * 1024


@dataclass(slots=True)
class StoredFile:
    record: File
    linked_message_id: UUID | None


def get_upload_limit_bytes(db: Session) -> int:
    settings_row = db.get(Settings, 1)
    upload_limit_mb = settings_row.upload_limit_mb_default if settings_row else DEFAULT_UPLOAD_LIMIT_MB
    return upload_limit_mb * 1024 * 1024


def ensure_uploads_root() -> Path:
    settings = get_settings()
    uploads_root = Path(settings.uploads_path).expanduser()
    uploads_root.mkdir(parents=True, exist_ok=True)
    return uploads_root.resolve()


def resolve_default_message_id(db: Session, *, conversation_id: UUID) -> UUID | None:
    return db.execute(
        select(Message.id)
        .where(
            Message.conversation_id == conversation_id,
            Message.role == "user",
            Message.archived_at.is_(None),
        )
        .order_by(Message.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def validate_message_in_conversation(
    db: Session,
    *,
    conversation_id: UUID,
    message_id: UUID,
) -> None:
    message = db.execute(
        select(Message.id).where(
            Message.id == message_id,
            Message.conversation_id == conversation_id,
            Message.archived_at.is_(None),
        )
    ).scalar_one_or_none()
    if message is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="Message not found in conversation",
            details={"conversation_id": str(conversation_id), "message_id": str(message_id)},
        )


def store_uploaded_file(
    db: Session,
    *,
    conversation_id: UUID,
    upload: UploadFile,
    message_id: UUID | None,
    max_upload_bytes: int,
) -> StoredFile:
    original_name = (upload.filename or "").strip() or "upload.bin"
    mime_type = (upload.content_type or "").strip() or "application/octet-stream"
    file_id = uuid4()

    uploads_root = ensure_uploads_root()
    conversation_dir = uploads_root / str(conversation_id)
    conversation_dir.mkdir(parents=True, exist_ok=True)

    safe_name = _sanitize_filename(original_name)
    relative_path = Path(str(conversation_id)) / f"{file_id}_{safe_name}"
    absolute_path = (uploads_root / relative_path).resolve()
    if uploads_root not in absolute_path.parents:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="BAD_REQUEST",
            message="Invalid upload path",
            details={},
        )

    bytes_written = 0
    temp_path = absolute_path.with_suffix(absolute_path.suffix + ".tmp")
    try:
        with temp_path.open("wb") as tmp_file:
            while True:
                chunk = upload.file.read(_CHUNK_SIZE_BYTES)
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > max_upload_bytes:
                    raise AppError(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        code="FILE_TOO_LARGE",
                        message="Uploaded file exceeds configured size limit",
                        details={
                            "file_name": original_name,
                            "max_size_bytes": max_upload_bytes,
                            "received_size_bytes": bytes_written,
                        },
                    )
                tmp_file.write(chunk)
        os.replace(temp_path, absolute_path)
    except Exception:
        _cleanup_file(temp_path)
        _cleanup_file(absolute_path)
        raise
    finally:
        upload.file.close()

    file_record = File(
        id=file_id,
        conversation_id=conversation_id,
        original_name=original_name,
        storage_path=relative_path.as_posix(),
        mime_type=mime_type,
        size_bytes=bytes_written,
    )
    db.add(file_record)
    if message_id is not None:
        db.add(MessageFile(message_id=message_id, file_id=file_id))
    db.flush()
    db.refresh(file_record)
    return StoredFile(record=file_record, linked_message_id=message_id)


def get_active_file(db: Session, *, file_id: UUID) -> File | None:
    return db.execute(
        select(File).where(File.id == file_id, File.archived_at.is_(None))
    ).scalar_one_or_none()


def resolve_file_absolute_path(file_record: File) -> Path:
    uploads_root = ensure_uploads_root()
    candidate = (uploads_root / file_record.storage_path).resolve()
    if uploads_root not in candidate.parents:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="BAD_REQUEST",
            message="Invalid file storage path",
            details={"file_id": str(file_record.id)},
        )
    return candidate


def get_files_for_message(db: Session, *, message_id: UUID) -> list[File]:
    stmt = (
        select(File)
        .join(MessageFile, MessageFile.file_id == File.id)
        .where(
            MessageFile.message_id == message_id,
            File.archived_at.is_(None),
        )
        .order_by(File.created_at.asc())
    )
    return list(db.execute(stmt).scalars())


def assign_files_to_message(
    db: Session,
    *,
    conversation_id: UUID,
    message_id: UUID,
    file_ids: list[UUID],
) -> list[File]:
    if not file_ids:
        return get_files_for_message(db, message_id=message_id)

    deduped_file_ids = list(dict.fromkeys(file_ids))
    file_rows = list(
        db.execute(
            select(File).where(
                File.id.in_(deduped_file_ids),
                File.conversation_id == conversation_id,
                File.archived_at.is_(None),
            )
        ).scalars()
    )
    found_ids = {row.id for row in file_rows}
    missing_ids = [str(file_id) for file_id in deduped_file_ids if file_id not in found_ids]
    if missing_ids:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="One or more files were not found in conversation",
            details={
                "conversation_id": str(conversation_id),
                "missing_file_ids": missing_ids,
            },
        )

    existing_links = {
        file_id
        for file_id in db.execute(
            select(MessageFile.file_id).where(
                MessageFile.message_id == message_id,
                MessageFile.file_id.in_(deduped_file_ids),
            )
        ).scalars()
    }
    for file_id in deduped_file_ids:
        if file_id in existing_links:
            continue
        db.add(MessageFile(message_id=message_id, file_id=file_id))
    db.flush()

    ordering = {file_id: idx for idx, file_id in enumerate(deduped_file_ids)}
    file_rows.sort(key=lambda row: ordering[row.id])
    return file_rows


def _sanitize_filename(filename: str) -> str:
    base_name = Path(filename).name.strip().replace(" ", "_")
    if not base_name:
        return "upload.bin"
    sanitized = _FILENAME_SANITIZE_PATTERN.sub("_", base_name)
    return sanitized[:200] if sanitized else "upload.bin"


def _cleanup_file(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except Exception:
        return
