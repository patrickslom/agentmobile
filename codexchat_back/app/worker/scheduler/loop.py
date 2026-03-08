from __future__ import annotations

import asyncio
import logging

from app.core.config import get_settings
from app.db.maintenance import cleanup_stale_locks
from app.db.session import SessionLocal
from app.worker.heartbeat.service import heartbeat_service
from app.worker.jobs.runner import run_claimed_heartbeat_run
from app.worker.title_summary.runner import run_claimed_title_summary_job
from app.worker.title_summary.service import title_summary_service

logger = logging.getLogger("app.worker")


async def run_scheduler_loop(*, stop_event: asyncio.Event) -> None:
    settings = get_settings()
    poll_interval_seconds = settings.heartbeat_poll_interval_seconds
    logger.info(
        "heartbeat_scheduler_started",
        extra={"event_data": {"poll_interval_seconds": poll_interval_seconds}},
    )
    while not stop_event.is_set():
        try:
            with SessionLocal() as db:
                stale_lock_count = cleanup_stale_locks(db)
                stale_run_count = heartbeat_service.recover_stale_running_runs(db)
                stale_title_summary_count = title_summary_service.recover_stale_running_jobs(db)
            with SessionLocal() as db:
                claimed = heartbeat_service.claim_due_runs(db)
                claimed_title_summary_jobs = title_summary_service.claim_pending_jobs(db)
            if stale_lock_count or stale_run_count or stale_title_summary_count or claimed or claimed_title_summary_jobs:
                logger.info(
                    "heartbeat_scheduler_iteration",
                    extra={
                        "event_data": {
                            "stale_locks_recovered": stale_lock_count,
                            "stale_runs_recovered": stale_run_count,
                            "stale_title_summary_jobs_recovered": stale_title_summary_count,
                            "claimed_runs": len(claimed),
                            "claimed_title_summary_jobs": len(claimed_title_summary_jobs),
                        }
                    },
                )
            for run in claimed:
                await run_claimed_heartbeat_run(run)
            for job in claimed_title_summary_jobs:
                await run_claimed_title_summary_job(job)
        except Exception:
            logger.exception("heartbeat_scheduler_iteration_failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=poll_interval_seconds)
        except TimeoutError:
            pass
