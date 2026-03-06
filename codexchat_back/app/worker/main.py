import logging

from fastapi import FastAPI
from sqlalchemy import text

from app.core.config import get_settings
from app.core.logging import RequestContextLoggingMiddleware, configure_logging
from app.db.migration_guard import assert_database_at_head
from app.db.session import engine

settings = get_settings()
configure_logging(pretty=settings.log_pretty, level=settings.log_level)
logger = logging.getLogger("app.worker")

app = FastAPI(title="CodexChat Worker")
app.add_middleware(RequestContextLoggingMiddleware)


@app.on_event("startup")
def on_startup() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        assert_database_at_head(connection)
    logger.info("worker_startup_complete")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
