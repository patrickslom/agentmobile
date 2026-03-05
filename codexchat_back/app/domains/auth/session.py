from __future__ import annotations

from uuid import UUID

from fastapi import WebSocket, WebSocketException, status
from sqlalchemy import select

from app.db.models import User
from app.db.session import SessionLocal

SESSION_COOKIE_NAME = "codexchat_session"


def _parse_user_id(raw_cookie: str | None) -> UUID | None:
    if not raw_cookie:
        return None
    try:
        return UUID(raw_cookie)
    except ValueError:
        return None


def _load_active_user(user_id: UUID | None) -> User | None:
    if user_id is None:
        return None

    with SessionLocal() as db:
        stmt = select(User).where(User.id == user_id, User.is_active.is_(True))
        return db.execute(stmt).scalar_one_or_none()


def authenticate_websocket(websocket: WebSocket) -> User:
    # Session auth is required for websocket upgrade. For now, the session
    # cookie stores the authenticated user UUID directly until full session
    # persistence is introduced in the sessions task.
    user_id = _parse_user_id(websocket.cookies.get(SESSION_COOKIE_NAME))
    user = _load_active_user(user_id)
    if user is None:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="AUTH_INVALID",
        )
    return user
