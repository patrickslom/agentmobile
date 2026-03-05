import contextvars
import json
import logging
import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)
conversation_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "conversation_id", default=None
)


class CodexChatJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(),
            "conversation_id": conversation_id_ctx.get(),
        }

        event_data = getattr(record, "event_data", None)
        if isinstance(event_data, dict):
            payload.update(event_data)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


class CodexChatPrettyFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        req = request_id_ctx.get() or "-"
        conv = conversation_id_ctx.get() or "-"
        message = f"{timestamp} {record.levelname:<8} {record.name} req={req} conv={conv} {record.getMessage()}"
        event_data = getattr(record, "event_data", None)
        if isinstance(event_data, dict) and event_data:
            message += f" {event_data}"
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"
        return message


def configure_logging(*, pretty: bool, level: str) -> None:
    formatter: logging.Formatter
    if pretty:
        formatter = CodexChatPrettyFormatter()
    else:
        formatter = CodexChatJsonFormatter()

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(level)

    for noisy in ("uvicorn.access",):
        logging.getLogger(noisy).setLevel(logging.WARNING)


class RequestContextLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        conversation_id = request.headers.get("x-conversation-id") or request.query_params.get(
            "conversation_id"
        )
        request_id_token = request_id_ctx.set(request_id)
        conversation_id_token = conversation_id_ctx.set(conversation_id)
        started = time.perf_counter()
        status_code = 500
        logger = logging.getLogger("app.request")
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.info(
                "http_request",
                extra={
                    "event_data": {
                        "request_id": request_id,
                        "conversation_id": conversation_id,
                        "user_id": getattr(request.state, "user_id", None),
                        "ip": request.client.host if request.client else None,
                        "path": request.url.path,
                        "method": request.method,
                        "status": status_code,
                        "duration_ms": elapsed_ms,
                    }
                },
            )
            request_id_ctx.reset(request_id_token)
            conversation_id_ctx.reset(conversation_id_token)
