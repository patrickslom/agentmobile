from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, WebSocket
from sqlalchemy import text

from app.api import api_router
from app.core.config import get_settings
from app.core.logging import RequestContextLoggingMiddleware, configure_logging
from app.db.session import engine

settings = get_settings()
configure_logging(pretty=settings.log_pretty, level=settings.log_level)
logger = logging.getLogger("app.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail fast when the configured database is unreachable.
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    logger.info("api_startup_complete")
    yield


app = FastAPI(title="CodexChat API", lifespan=lifespan)
app.add_middleware(RequestContextLoggingMiddleware)
app.include_router(api_router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_probe(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.close(code=1000)
