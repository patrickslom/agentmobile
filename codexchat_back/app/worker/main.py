import logging

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import RequestContextLoggingMiddleware, configure_logging

settings = get_settings()
configure_logging(pretty=settings.log_pretty, level=settings.log_level)
logger = logging.getLogger("app.worker")

app = FastAPI(title="CodexChat Worker")
app.add_middleware(RequestContextLoggingMiddleware)


@app.on_event("startup")
def on_startup() -> None:
    logger.info("worker_startup_complete")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
