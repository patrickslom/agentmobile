from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import AuthAttempt

LOCKOUT_DURATIONS = {
    1: timedelta(minutes=5),
    2: timedelta(minutes=30),
    3: timedelta(hours=6),
    4: timedelta(days=7),
}
REDIS_KEY_PREFIX = "agentmobile:auth_attempt:"


@dataclass(slots=True)
class AttemptState:
    fail_count: int = 0
    ban_level: int = 0
    ban_until: datetime | None = None
    last_failed_at: datetime | None = None


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


def _email_ip_key(email: str, ip: str) -> str:
    return f"email_ip:{email}|{ip}"


def _ip_key(ip: str) -> str:
    return f"ip:{ip}"


def _keys(email: str, ip: str) -> tuple[str, str]:
    return _email_ip_key(email.strip().lower(), ip), _ip_key(ip)


class LockoutService:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._redis: Redis | None = None
        if self._settings.redis_url:
            self._redis = Redis.from_url(
                self._settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=0.2,
                socket_timeout=0.2,
            )

    def is_locked(self, db: Session, *, email: str, ip: str) -> datetime | None:
        now = _utcnow()
        candidates: list[datetime] = []
        for key in _keys(email, ip):
            state = self._read_state(db, key)
            if state.ban_until and state.ban_until > now:
                candidates.append(state.ban_until)
        if not candidates:
            return None
        return max(candidates)

    def register_failure(self, db: Session, *, email: str, ip: str) -> datetime | None:
        now = _utcnow()
        ban_until: datetime | None = None
        for key in _keys(email, ip):
            state = self._read_state(db, key)
            state.fail_count += 1
            state.last_failed_at = now
            state.ban_level = min(max(state.fail_count - 2, 0), 4)
            if state.ban_level > 0:
                state.ban_until = now + LOCKOUT_DURATIONS[state.ban_level]
                ban_until = max(ban_until, state.ban_until) if ban_until else state.ban_until
            else:
                state.ban_until = None
            self._write_state(db, key=key, email=email, ip=ip, state=state)
        return ban_until

    def clear_failures(self, db: Session, *, email: str, ip: str) -> None:
        for key in _keys(email, ip):
            self._delete_state(db, key)

    def _read_state(self, db: Session, key: str) -> AttemptState:
        redis_state = self._read_state_redis(key)
        if redis_state is not None:
            return redis_state

        row = db.execute(select(AuthAttempt).where(AuthAttempt.key == key)).scalar_one_or_none()
        if row is None:
            return AttemptState()
        return AttemptState(
            fail_count=row.fail_count,
            ban_level=row.ban_level,
            ban_until=row.ban_until,
            last_failed_at=row.last_failed_at,
        )

    def _write_state(self, db: Session, *, key: str, email: str, ip: str, state: AttemptState) -> None:
        if self._write_state_redis(key, state):
            return

        row = db.execute(select(AuthAttempt).where(AuthAttempt.key == key)).scalar_one_or_none()
        normalized_email = email.strip().lower() or None
        normalized_ip = ip or None
        if row is None:
            row = AuthAttempt(key=key, email=normalized_email, ip=normalized_ip)
            db.add(row)
        row.fail_count = state.fail_count
        row.ban_level = state.ban_level
        row.ban_until = state.ban_until
        row.last_failed_at = state.last_failed_at
        db.commit()

    def _delete_state(self, db: Session, key: str) -> None:
        if self._delete_state_redis(key):
            return
        row = db.execute(select(AuthAttempt).where(AuthAttempt.key == key)).scalar_one_or_none()
        if row is not None:
            db.delete(row)
            db.commit()

    def _redis_key(self, key: str) -> str:
        return f"{REDIS_KEY_PREFIX}{key}"

    def _read_state_redis(self, key: str) -> AttemptState | None:
        if self._redis is None:
            return None
        try:
            payload = self._redis.hgetall(self._redis_key(key))
        except RedisError:
            return None
        if not payload:
            return None
        return AttemptState(
            fail_count=int(payload.get("fail_count", "0")),
            ban_level=int(payload.get("ban_level", "0")),
            ban_until=_parse_datetime(payload.get("ban_until")),
            last_failed_at=_parse_datetime(payload.get("last_failed_at")),
        )

    def _write_state_redis(self, key: str, state: AttemptState) -> bool:
        if self._redis is None:
            return False
        redis_key = self._redis_key(key)
        payload = {
            "fail_count": str(state.fail_count),
            "ban_level": str(state.ban_level),
            "ban_until": state.ban_until.isoformat() if state.ban_until else "",
            "last_failed_at": state.last_failed_at.isoformat() if state.last_failed_at else "",
        }
        try:
            self._redis.hset(redis_key, mapping=payload)
            self._redis.expire(redis_key, int(timedelta(days=8).total_seconds()))
        except RedisError:
            return False
        return True

    def _delete_state_redis(self, key: str) -> bool:
        if self._redis is None:
            return False
        try:
            self._redis.delete(self._redis_key(key))
        except RedisError:
            return False
        return True


lockout_service = LockoutService()
