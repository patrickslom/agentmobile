from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.errors import build_error_envelope
from app.domains.auth.session import session_manager

CSRF_EXEMPT_PATHS = {
    "/api/auth/login",
    "/api/auth/logout",
    "/api/auth/register",
}
STATEFUL_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if self._requires_csrf_check(request):
            session_cookie = request.cookies.get(session_manager.session_cookie_name)
            csrf_cookie = request.cookies.get(session_manager.csrf_cookie_name)
            csrf_header = request.headers.get("x-csrf-token")
            session_id = session_manager.parse_cookie_value(session_cookie)

            is_valid = (
                session_id is not None
                and bool(csrf_cookie)
                and bool(csrf_header)
                and csrf_cookie == csrf_header
                and csrf_cookie == session_manager.csrf_for_session(session_id)
            )
            if not is_valid:
                return JSONResponse(
                    status_code=403,
                    content=build_error_envelope(
                        code="CSRF_INVALID",
                        message="CSRF token validation failed",
                        details={},
                        request_id=request.headers.get("x-request-id", ""),
                    ),
                )

        return await call_next(request)

    def _requires_csrf_check(self, request: Request) -> bool:
        path = request.url.path
        if request.method.upper() not in STATEFUL_METHODS:
            return False
        if not path.startswith("/api/"):
            return False
        if path in CSRF_EXEMPT_PATHS:
            return False
        return True
