from contextlib import asynccontextmanager
import logging
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import api_router
from app.core.config import get_settings
from app.core.csrf import CSRFMiddleware
from app.core.errors import AppError, build_error_envelope
from app.core.logging import RequestContextLoggingMiddleware, configure_logging, request_id_ctx
from app.domains.auth.password import ensure_password_backend
from app.domains.auth.session import authenticate_websocket
from app.domains.chat.websocket import chat_websocket_service
from app.db.bootstrap import seed_defaults
from app.db.migration_guard import assert_database_at_head
from app.db.session import engine

settings = get_settings()
configure_logging(pretty=settings.log_pretty, level=settings.log_level)
logger = logging.getLogger("app.api")

OPENAPI_TAGS = [
    {"name": "auth", "description": "Authentication and session lifecycle."},
    {"name": "chat", "description": "Conversation and message APIs."},
    {"name": "bookmarks", "description": "User-scoped assistant message bookmarks."},
    {"name": "codex", "description": "Codex runtime bridge operations."},
    {"name": "files", "description": "Conversation file upload and download."},
    {"name": "heartbeat", "description": "Heartbeat job scheduling and run logs."},
    {"name": "settings", "description": "Application and runtime settings."},
    {"name": "admin", "description": "Administrative user management."},
    {"name": "locks", "description": "Conversation lock and busy-state APIs."},
    {"name": "system", "description": "Health and service diagnostics."},
]


def _current_request_id(request: Request) -> str:
    return request_id_ctx.get() or request.headers.get("x-request-id") or str(uuid4())


def _http_code_for_status(status_code: int) -> str:
    mapping = {
        400: "BAD_REQUEST",
        401: "AUTH_INVALID",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        413: "PAYLOAD_TOO_LARGE",
        415: "UNSUPPORTED_MEDIA_TYPE",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
    }
    return mapping.get(status_code, "HTTP_ERROR")


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_password_backend()
    # Fail fast when the configured database is unreachable.
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        assert_database_at_head(connection)
    with Session(engine) as db:
        seed_result = seed_defaults(db)
    logger.info("api_startup_complete")
    if seed_result["seeded_settings"] or seed_result["seeded_admin"]:
        logger.info("db_seed_applied", extra={"event_data": seed_result})
    yield


app = FastAPI(
    title="CodexChat API",
    lifespan=lifespan,
    openapi_tags=OPENAPI_TAGS,
)
app.add_middleware(RequestContextLoggingMiddleware)
app.add_middleware(CSRFMiddleware)
app.include_router(api_router, prefix="/api")


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_envelope(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            request_id=_current_request_id(request),
        ),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail_message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_envelope(
            code=_http_code_for_status(exc.status_code),
            message=detail_message,
            details={},
            request_id=_current_request_id(request),
        ),
    )


@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    detail_message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_envelope(
            code=_http_code_for_status(exc.status_code),
            message=detail_message,
            details={},
            request_id=_current_request_id(request),
        ),
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=build_error_envelope(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details={"errors": exc.errors()},
            request_id=_current_request_id(request),
        ),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content=build_error_envelope(
            code="INTERNAL",
            message="Internal server error",
            details={},
            request_id=_current_request_id(request),
        ),
    )


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/health", tags=["system"])
def api_health() -> dict[str, str]:
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_probe(websocket: WebSocket) -> None:
    user = authenticate_websocket(websocket)
    await chat_websocket_service.handle_connection(websocket, user=user)
