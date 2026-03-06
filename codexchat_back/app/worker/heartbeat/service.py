from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import HeartbeatJob, HeartbeatRun, HeartbeatSchedule


@dataclass(slots=True)
class ClaimedHeartbeatRun:
    run_id: UUID
    heartbeat_job_id: UUID
    conversation_id: UUID
    instruction_file_path: str


class HeartbeatService:
    def __init__(self) -> None:
        settings = get_settings()
        self._claim_batch_size = settings.heartbeat_claim_batch_size
        self._stale_after_seconds = settings.heartbeat_run_stale_after_seconds

    def recover_stale_running_runs(self, db: Session) -> int:
        cutoff = datetime.now(tz=UTC) - timedelta(seconds=self._stale_after_seconds)
        result = db.execute(
            update(HeartbeatRun)
            .where(
                HeartbeatRun.status == "running",
                HeartbeatRun.started_at.is_not(None),
                HeartbeatRun.started_at < cutoff,
                HeartbeatRun.finished_at.is_(None),
            )
            .values(
                status="failed",
                finished_at=datetime.now(tz=UTC),
                error_text="Heartbeat run marked failed after stale timeout",
            )
        )
        db.commit()
        return result.rowcount or 0

    def claim_due_runs(self, db: Session) -> list[ClaimedHeartbeatRun]:
        now = datetime.now(tz=UTC)
        rows = list(
            db.execute(
                select(HeartbeatSchedule, HeartbeatJob)
                .join(HeartbeatJob, HeartbeatJob.id == HeartbeatSchedule.heartbeat_job_id)
                .where(
                    HeartbeatJob.archived_at.is_(None),
                    HeartbeatJob.enabled.is_(True),
                    HeartbeatSchedule.next_run_at <= now,
                )
                .order_by(HeartbeatSchedule.next_run_at.asc())
                .limit(self._claim_batch_size)
                .with_for_update(skip_locked=True, of=HeartbeatSchedule)
            )
        )
        if not rows:
            db.rollback()
            return []

        claimed: list[ClaimedHeartbeatRun] = []
        for schedule, job in rows:
            run = HeartbeatRun(
                heartbeat_job_id=job.id,
                status="running",
                started_at=now,
                finished_at=None,
                error_text=None,
            )
            schedule.last_run_at = now
            schedule.next_run_at = now + timedelta(minutes=schedule.interval_minutes)
            db.add(run)
            db.flush()
            claimed.append(
                ClaimedHeartbeatRun(
                    run_id=run.id,
                    heartbeat_job_id=job.id,
                    conversation_id=job.conversation_id,
                    instruction_file_path=job.instruction_file_path,
                )
            )

        db.commit()
        return claimed

    def mark_run_succeeded(self, db: Session, *, run_id: UUID) -> None:
        db.execute(
            update(HeartbeatRun)
            .where(HeartbeatRun.id == run_id)
            .values(
                status="succeeded",
                finished_at=datetime.now(tz=UTC),
                error_text=None,
            )
        )
        db.commit()

    def mark_run_failed(self, db: Session, *, run_id: UUID, error_text: str) -> None:
        db.execute(
            update(HeartbeatRun)
            .where(HeartbeatRun.id == run_id)
            .values(
                status="failed",
                finished_at=datetime.now(tz=UTC),
                error_text=error_text[:4000],
            )
        )
        db.commit()


heartbeat_service = HeartbeatService()
