from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.archive_queries import get_conversation
from app.db.models import HeartbeatJob, HeartbeatRun, HeartbeatSchedule, Settings, User
from app.db.session import get_db
from app.domains.auth.dependencies import get_current_user

router = APIRouter(prefix="/heartbeat-jobs", tags=["heartbeat"])
settings = get_settings()


class HeartbeatJobCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID
    instruction_file_path: str = Field(min_length=1, max_length=2048)
    interval_minutes: int = Field(ge=1)
    enabled: bool | None = None


class HeartbeatJobPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instruction_file_path: str | None = Field(default=None, min_length=1, max_length=2048)
    interval_minutes: int | None = Field(default=None, ge=1)
    enabled: bool | None = None


class HeartbeatJobResponse(BaseModel):
    id: str
    conversation_id: str
    instruction_file_path: str
    interval_minutes: int
    next_run_at: datetime
    last_run_at: datetime | None
    enabled: bool
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None
    is_archived: bool


class HeartbeatRunResponse(BaseModel):
    id: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    error_text: str | None
    created_at: datetime


def _ensure_settings_row(db: Session) -> Settings:
    row = db.get(Settings, 1)
    if row is None:
        row = Settings(id=1)
        db.add(row)
        db.flush()
    return row


def _validate_instruction_file_path(raw_path: str) -> str:
    path = Path(raw_path.strip())
    if not path.is_absolute():
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message="instruction_file_path must be an absolute path",
            details={},
        )
    if not path.exists():
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message="instruction_file_path must exist",
            details={},
        )
    if not path.is_file():
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message="instruction_file_path must point to a file",
            details={},
        )
    if path.suffix.lower() not in {".md", ".markdown", ".mdown"}:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message="instruction_file_path must be a markdown file",
            details={},
        )
    allowed_base_raw = settings.heartbeat_allowed_base_path
    if allowed_base_raw:
        allowed_base = Path(allowed_base_raw).expanduser().resolve()
        resolved = path.expanduser().resolve()
        if resolved != allowed_base and allowed_base not in resolved.parents:
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                code="VALIDATION_ERROR",
                message="instruction_file_path is outside allowed base path",
                details={"allowed_base_path": str(allowed_base)},
            )
        return str(resolved)
    return str(path.expanduser().resolve())


def _validate_interval_minutes(interval_minutes: int) -> None:
    if interval_minutes < settings.heartbeat_min_interval_minutes:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message="Interval is below minimum heartbeat interval",
            details={"min_interval_minutes": settings.heartbeat_min_interval_minutes},
        )
    presets = tuple(v for v in settings.heartbeat_interval_presets if v >= settings.heartbeat_min_interval_minutes)
    if presets and interval_minutes not in presets:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message="Interval must match one of the configured presets",
            details={"allowed_interval_minutes": list(presets)},
        )


def _enforce_job_cap(db: Session) -> None:
    settings_row = _ensure_settings_row(db)
    if settings_row.heartbeat_unlimited_default:
        return
    active_count = db.execute(
        select(func.count())
        .select_from(HeartbeatJob)
        .where(HeartbeatJob.archived_at.is_(None))
    ).scalar_one()
    if active_count >= settings_row.heartbeat_cap_default:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            code="HEARTBEAT_CAP_REACHED",
            message="Heartbeat job cap reached",
            details={
                "cap": settings_row.heartbeat_cap_default,
                "active_jobs": active_count,
            },
        )


def _to_response(job: HeartbeatJob, schedule: HeartbeatSchedule) -> HeartbeatJobResponse:
    return HeartbeatJobResponse(
        id=str(job.id),
        conversation_id=str(job.conversation_id),
        instruction_file_path=job.instruction_file_path,
        interval_minutes=schedule.interval_minutes,
        next_run_at=schedule.next_run_at,
        last_run_at=schedule.last_run_at,
        enabled=job.enabled,
        created_at=job.created_at,
        updated_at=job.updated_at,
        archived_at=job.archived_at,
        is_archived=job.archived_at is not None,
    )


def _recent_runs_for_jobs(db: Session, *, job_ids: list[UUID], limit_per_job: int = 3) -> dict[UUID, list[HeartbeatRun]]:
    if not job_ids:
        return {}
    rows = db.execute(
        select(HeartbeatRun)
        .where(HeartbeatRun.heartbeat_job_id.in_(job_ids))
        .order_by(HeartbeatRun.created_at.desc())
    ).scalars()
    grouped: dict[UUID, list[HeartbeatRun]] = {}
    for row in rows:
        bucket = grouped.setdefault(row.heartbeat_job_id, [])
        if len(bucket) < limit_per_job:
            bucket.append(row)
    return grouped


@router.get("")
def list_heartbeat_jobs(
    include_archived: bool = Query(default=False),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, list[dict[str, object]]]:
    stmt = (
        select(HeartbeatJob, HeartbeatSchedule)
        .join(HeartbeatSchedule, HeartbeatSchedule.heartbeat_job_id == HeartbeatJob.id)
        .order_by(HeartbeatJob.created_at.asc())
    )
    if not include_archived:
        stmt = stmt.where(HeartbeatJob.archived_at.is_(None))

    rows = list(db.execute(stmt))
    jobs = [_to_response(job, schedule) for job, schedule in rows]
    recent_runs = _recent_runs_for_jobs(db, job_ids=[job.id for job, _ in rows])
    recent_runs_by_job_id = {str(job_id): runs for job_id, runs in recent_runs.items()}
    return {
        "heartbeat_jobs": [
            {
                **job.model_dump(),
                "runs": [
                    HeartbeatRunResponse(
                        id=str(run.id),
                        status=run.status,
                        started_at=run.started_at,
                        finished_at=run.finished_at,
                        error_text=run.error_text,
                        created_at=run.created_at,
                    ).model_dump()
                    for run in recent_runs_by_job_id.get(job.id, [])
                ],
            }
            for job in jobs
        ]
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_heartbeat_job(
    payload: HeartbeatJobCreateRequest,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, HeartbeatJobResponse]:
    conversation = get_conversation(db, payload.conversation_id, include_archived=False)
    if conversation is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="Conversation not found",
            details={"conversation_id": str(payload.conversation_id)},
        )

    _validate_interval_minutes(payload.interval_minutes)
    normalized_path = _validate_instruction_file_path(payload.instruction_file_path)
    _enforce_job_cap(db)

    settings_row = _ensure_settings_row(db)
    enabled = payload.enabled if payload.enabled is not None else settings_row.heartbeat_enabled_default
    now = datetime.now(tz=UTC)

    job = HeartbeatJob(
        conversation_id=payload.conversation_id,
        instruction_file_path=normalized_path,
        enabled=enabled,
    )
    db.add(job)
    db.flush()
    schedule = HeartbeatSchedule(
        heartbeat_job_id=job.id,
        interval_minutes=payload.interval_minutes,
        next_run_at=now + timedelta(minutes=payload.interval_minutes),
        last_run_at=None,
    )
    db.add(schedule)
    db.commit()
    db.refresh(job)
    db.refresh(schedule)
    return {"heartbeat_job": _to_response(job, schedule)}


@router.patch("/{heartbeat_job_id}")
def patch_heartbeat_job(
    heartbeat_job_id: UUID,
    payload: HeartbeatJobPatchRequest,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, HeartbeatJobResponse]:
    provided_fields = payload.model_fields_set
    if not provided_fields:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="BAD_REQUEST",
            message="No updates were provided",
            details={},
        )

    row = db.execute(
        select(HeartbeatJob, HeartbeatSchedule)
        .join(HeartbeatSchedule, HeartbeatSchedule.heartbeat_job_id == HeartbeatJob.id)
        .where(HeartbeatJob.id == heartbeat_job_id)
    ).one_or_none()
    if row is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="Heartbeat job not found",
            details={"heartbeat_job_id": str(heartbeat_job_id)},
        )
    job, schedule = row
    if job.archived_at is not None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="Heartbeat job not found",
            details={"heartbeat_job_id": str(heartbeat_job_id)},
        )

    if "instruction_file_path" in provided_fields:
        if payload.instruction_file_path is None:
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                code="VALIDATION_ERROR",
                message="instruction_file_path cannot be null",
                details={},
            )
        job.instruction_file_path = _validate_instruction_file_path(payload.instruction_file_path)
    if "interval_minutes" in provided_fields:
        if payload.interval_minutes is None:
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                code="VALIDATION_ERROR",
                message="interval_minutes cannot be null",
                details={},
            )
        _validate_interval_minutes(payload.interval_minutes)
        schedule.interval_minutes = payload.interval_minutes
        schedule.next_run_at = datetime.now(tz=UTC) + timedelta(minutes=payload.interval_minutes)
    if "enabled" in provided_fields:
        if payload.enabled is None:
            raise AppError(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                code="VALIDATION_ERROR",
                message="enabled cannot be null",
                details={},
            )
        job.enabled = payload.enabled

    db.commit()
    db.refresh(job)
    db.refresh(schedule)
    return {"heartbeat_job": _to_response(job, schedule)}


@router.delete("/{heartbeat_job_id}")
def delete_heartbeat_job(
    heartbeat_job_id: UUID,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    job = db.get(HeartbeatJob, heartbeat_job_id)
    if job is None or job.archived_at is not None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="Heartbeat job not found",
            details={"heartbeat_job_id": str(heartbeat_job_id)},
        )
    job.enabled = False
    job.archived_at = datetime.now(tz=UTC)
    db.commit()
    return {"ok": True, "heartbeat_job_id": str(heartbeat_job_id)}
