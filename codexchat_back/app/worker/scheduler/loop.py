from __future__ import annotations

import asyncio
import logging

from app.core.config import get_settings
from app.db.maintenance import cleanup_stale_locks
from app.db.session import SessionLocal
from app.worker.heartbeat.service import heartbeat_service
from app.worker.jobs.runner import run_claimed_heartbeat_run

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
            with SessionLocal() as db:
                claimed = heartbeat_service.claim_due_runs(db)
            if stale_lock_count or stale_run_count or claimed:
                logger.info(
                    "heartbeat_scheduler_iteration",
                    extra={
                        "event_data": {
                            "stale_locks_recovered": stale_lock_count,
                            "stale_runs_recovered": stale_run_count,
                            "claimed_runs": len(claimed),
                        }
                    },
                )
            for run in claimed:
                await run_claimed_heartbeat_run(run)
        except Exception:
            logger.exception("heartbeat_scheduler_iteration_failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=poll_interval_seconds)
        except TimeoutError:
            pass
