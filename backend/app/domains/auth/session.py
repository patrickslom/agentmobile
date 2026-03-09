from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse
from uuid import UUID, uuid4

from fastapi import WebSocket, WebSocketException, status
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Session as SessionModel
from app.db.models import User
from app.db.session import SessionLocal


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _parse_datetime(raw_value: str | None) -> datetime | None:
    if not raw_value:
        return None
    try:
        parsed = datetime.fromisoformat(raw_value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


@dataclass(slots=True)
class AuthSession:
    session_id: str
    user_id: UUID
    expires_at: datetime
    cookie_value: str


class SessionManager:
    def __init__(self) -> None:
        self._settings = get_settings()
        self.session_cookie_name = self._settings.session_cookie_name
        self.csrf_cookie_name = self._settings.csrf_cookie_name
        self.ttl = timedelta(hours=self._settings.session_ttl_hours)
        self._secret = self._settings.session_secret.encode("utf-8")
        self._redis: Redis | None = None
        if self._settings.redis_url:
            self._redis = Redis.from_url(
                self._settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=0.2,
                socket_timeout=0.2,
            )

    def _sign_session_id(self, session_id: str) -> str:
        digest = hmac.new(self._secret, session_id.encode("utf-8"), hashlib.sha256).digest()
        return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")

    def build_cookie_value(self, session_id: str) -> str:
        signature = self._sign_session_id(session_id)
        return f"{session_id}.{signature}"

    def parse_cookie_value(self, cookie_value: str | None) -> str | None:
        if not cookie_value:
            return None
        if "." not in cookie_value:
            return None
        session_id, signature = cookie_value.split(".", maxsplit=1)
        if not session_id or not signature:
            return None
        expected = self._sign_session_id(session_id)
        if not hmac.compare_digest(expected, signature):
            return None
        try:
            UUID(session_id)
        except ValueError:
            return None
        return session_id

    def csrf_for_session(self, session_id: str) -> str:
        digest = hmac.new(self._secret, f"csrf:{session_id}".encode("utf-8"), hashlib.sha256).digest()
        return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")

    def _token_hash(self, session_id: str) -> str:
        return hashlib.sha256(session_id.encode("utf-8")).hexdigest()

    def _redis_key(self, session_id: str) -> str:
        return f"agentmobile:session:{session_id}"

    def create_session(self, db: Session, *, user_id: UUID) -> AuthSession:
        session_id = str(uuid4())
        now = _utcnow()
        expires_at = now + self.ttl
        token_hash = self._token_hash(session_id)

        db.add(
            SessionModel(
                user_id=user_id,
                token_hash=token_hash,
                last_seen_at=now,
                expires_at=expires_at,
                revoked_at=None,
            )
        )
        db.commit()
        self._cache_session(session_id=session_id, user_id=user_id, expires_at=expires_at)
        return AuthSession(
            session_id=session_id,
            user_id=user_id,
            expires_at=expires_at,
            cookie_value=self.build_cookie_value(session_id),
        )

    def revoke_session(self, db: Session, *, session_id: str) -> None:
        token_hash = self._token_hash(session_id)
        record = db.execute(select(SessionModel).where(SessionModel.token_hash == token_hash)).scalar_one_or_none()
        if record is not None and record.revoked_at is None:
            record.revoked_at = _utcnow()
            db.commit()
        self._uncache_session(session_id)

    def resolve_session(self, db: Session, *, cookie_value: str | None) -> AuthSession | None:
        session_id = self.parse_cookie_value(cookie_value)
        if session_id is None:
            return None

        cached = self._get_cached_session(session_id)
        if cached is not None:
            return cached

        token_hash = self._token_hash(session_id)
        record = db.execute(
            select(SessionModel, User)
            .join(User, User.id == SessionModel.user_id)
            .where(
                SessionModel.token_hash == token_hash,
                SessionModel.revoked_at.is_(None),
                SessionModel.expires_at > _utcnow(),
                User.is_active.is_(True),
            )
        ).one_or_none()
        if record is None:
            return None

        session_row, user_row = record
        session_row.last_seen_at = _utcnow()
        db.commit()
        resolved = AuthSession(
            session_id=session_id,
            user_id=user_row.id,
            expires_at=session_row.expires_at,
            cookie_value=cookie_value or self.build_cookie_value(session_id),
        )
        self._cache_session(
            session_id=session_id,
            user_id=user_row.id,
            expires_at=session_row.expires_at,
        )
        return resolved

    def _get_cached_session(self, session_id: str) -> AuthSession | None:
        if self._redis is None:
            return None
        try:
            payload = self._redis.hgetall(self._redis_key(session_id))
        except RedisError:
            return None
        if not payload:
            return None

        user_id_raw = payload.get("user_id")
        expires_raw = payload.get("expires_at")
        if not user_id_raw or not expires_raw:
            return None
        expires_at = _parse_datetime(expires_raw)
        if expires_at is None or expires_at <= _utcnow():
            return None
        try:
            user_id = UUID(user_id_raw)
        except ValueError:
            return None
        return AuthSession(
            session_id=session_id,
            user_id=user_id,
            expires_at=expires_at,
            cookie_value=self.build_cookie_value(session_id),
        )

    def _cache_session(self, *, session_id: str, user_id: UUID, expires_at: datetime) -> None:
        if self._redis is None:
            return
        ttl_seconds = int((expires_at - _utcnow()).total_seconds())
        if ttl_seconds <= 0:
            return
        payload = {
            "user_id": str(user_id),
            "expires_at": expires_at.isoformat(),
            "nonce": secrets.token_hex(4),
        }
        try:
            self._redis.hset(self._redis_key(session_id), mapping=payload)
            self._redis.expire(self._redis_key(session_id), ttl_seconds)
        except RedisError:
            return

    def _uncache_session(self, session_id: str) -> None:
        if self._redis is None:
            return
        try:
            self._redis.delete(self._redis_key(session_id))
        except RedisError:
            return


session_manager = SessionManager()


def _normalize_host_header(value: str | None) -> str | None:
    if not value:
        return None
    first = value.split(",", maxsplit=1)[0].strip().lower()
    if not first:
        return None
    if ":" in first and not first.startswith("["):
        first = first.split(":", maxsplit=1)[0]
    return first or None


def _validate_websocket_host_and_origin(websocket: WebSocket) -> None:
    settings = get_settings()
    request_host = _normalize_host_header(
        websocket.headers.get("x-forwarded-host") or websocket.headers.get("host")
    )
    if request_host is None:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="FORBIDDEN_HOST",
        )

    allowed_hosts = {host.lower() for host in settings.allowed_hosts}
    if "*" not in allowed_hosts and request_host not in allowed_hosts:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="FORBIDDEN_HOST",
        )

    origin = websocket.headers.get("origin")
    if not origin:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="FORBIDDEN_ORIGIN",
        )

    parsed_origin = urlparse(origin)
    origin_host = parsed_origin.hostname.lower() if parsed_origin.hostname else None
    if origin_host is None:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="FORBIDDEN_ORIGIN",
        )

    if origin_host != request_host:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="FORBIDDEN_ORIGIN",
        )

    allowed_origins = {allowed.lower() for allowed in settings.ws_allowed_origins}
    normalized_origin = origin.strip().lower()
    if allowed_origins and normalized_origin not in allowed_origins:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="FORBIDDEN_ORIGIN",
        )


def authenticate_websocket(websocket: WebSocket) -> User:
    _validate_websocket_host_and_origin(websocket)
    with SessionLocal() as db:
        auth_session = session_manager.resolve_session(
            db,
            cookie_value=websocket.cookies.get(session_manager.session_cookie_name),
        )
        if auth_session is None:
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="AUTH_INVALID",
            )

        user = db.execute(
            select(User).where(User.id == auth_session.user_id, User.is_active.is_(True))
        ).scalar_one_or_none()
        if user is None:
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="AUTH_INVALID",
            )
        return user
