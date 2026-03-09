import logging
import asyncio

from fastapi import FastAPI
from sqlalchemy import text

from app.core.config import get_settings
from app.core.logging import RequestContextLoggingMiddleware, configure_logging
from app.db.migration_guard import assert_database_at_head
from app.db.session import engine
from app.worker.scheduler.loop import run_scheduler_loop

settings = get_settings()
configure_logging(pretty=settings.log_pretty, level=settings.log_level)
logger = logging.getLogger("app.worker")

app = FastAPI(title="AGENTMOBILE Worker")
app.add_middleware(RequestContextLoggingMiddleware)
_scheduler_stop = asyncio.Event()
_scheduler_task: asyncio.Task[None] | None = None


@app.on_event("startup")
async def on_startup() -> None:
    global _scheduler_task
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        assert_database_at_head(connection)
    _scheduler_stop.clear()
    _scheduler_task = asyncio.create_task(run_scheduler_loop(stop_event=_scheduler_stop))
    logger.info("worker_startup_complete")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    global _scheduler_task
    _scheduler_stop.set()
    if _scheduler_task is not None:
        await _scheduler_task
        _scheduler_task = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
