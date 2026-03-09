from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models import ConversationTitleSummaryJob

TITLE_SUMMARY_CLAIM_BATCH_SIZE = 5
TITLE_SUMMARY_RETRY_DELAY_SECONDS = 300
TITLE_SUMMARY_STALE_AFTER_SECONDS = 900


@dataclass(slots=True)
class ClaimedTitleSummaryJob:
    job_id: UUID
    conversation_id: UUID
    attempt_count: int


class TitleSummaryService:
    def recover_stale_running_jobs(self, db: Session) -> int:
        cutoff = datetime.now(tz=UTC) - timedelta(seconds=TITLE_SUMMARY_STALE_AFTER_SECONDS)
        result = db.execute(
            update(ConversationTitleSummaryJob)
            .where(
                ConversationTitleSummaryJob.status == "running",
                ConversationTitleSummaryJob.started_at.is_not(None),
                ConversationTitleSummaryJob.started_at < cutoff,
            )
            .values(
                status="failed",
                finished_at=datetime.now(tz=UTC),
                available_at=datetime.now(tz=UTC) + timedelta(seconds=TITLE_SUMMARY_RETRY_DELAY_SECONDS),
                error_text="Title/summary generation marked failed after stale timeout",
            )
        )
        db.commit()
        return result.rowcount or 0

    def claim_pending_jobs(self, db: Session) -> list[ClaimedTitleSummaryJob]:
        now = datetime.now(tz=UTC)
        rows = list(
            db.execute(
                select(ConversationTitleSummaryJob)
                .where(
                    ConversationTitleSummaryJob.status.in_(("pending", "failed")),
                    ConversationTitleSummaryJob.available_at <= now,
                )
                .order_by(
                    ConversationTitleSummaryJob.requested_at.asc(),
                    ConversationTitleSummaryJob.created_at.asc(),
                )
                .limit(TITLE_SUMMARY_CLAIM_BATCH_SIZE)
                .with_for_update(skip_locked=True, of=ConversationTitleSummaryJob)
            ).scalars()
        )
        if not rows:
            db.rollback()
            return []

        claimed: list[ClaimedTitleSummaryJob] = []
        for row in rows:
            row.status = "running"
            row.started_at = now
            row.finished_at = None
            row.error_text = None
            row.attempt_count += 1
            claimed.append(
                ClaimedTitleSummaryJob(
                    job_id=row.id,
                    conversation_id=row.conversation_id,
                    attempt_count=row.attempt_count,
                )
            )

        db.commit()
        return claimed

    def mark_job_succeeded(self, db: Session, *, job_id: UUID) -> None:
        db.execute(
            update(ConversationTitleSummaryJob)
            .where(ConversationTitleSummaryJob.id == job_id)
            .values(
                status="completed",
                finished_at=datetime.now(tz=UTC),
                error_text=None,
            )
        )
        db.commit()

    def mark_job_failed(self, db: Session, *, job_id: UUID, error_text: str) -> None:
        db.execute(
            update(ConversationTitleSummaryJob)
            .where(ConversationTitleSummaryJob.id == job_id)
            .values(
                status="failed",
                finished_at=datetime.now(tz=UTC),
                available_at=datetime.now(tz=UTC) + timedelta(seconds=TITLE_SUMMARY_RETRY_DELAY_SECONDS),
                error_text=error_text[:4000],
            )
        )
        db.commit()


title_summary_service = TitleSummaryService()
