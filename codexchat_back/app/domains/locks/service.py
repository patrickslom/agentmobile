from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import ConversationLock

LOCK_TTL_SECONDS = 120


@dataclass(slots=True)
class LockState:
    conversation_id: UUID
    is_busy: bool
    locked_by: UUID | None
    reason: str
    owner_token: str | None


@dataclass(slots=True)
class LockAcquireResult:
    acquired: bool
    state: LockState


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _is_stale(lock: ConversationLock, now: datetime) -> bool:
    heartbeat_cutoff = lock.last_heartbeat_at + timedelta(seconds=lock.stale_after_seconds)
    return lock.expires_at <= now or heartbeat_cutoff <= now


class ConversationLockService:
    def acquire(
        self,
        db: Session,
        *,
        conversation_id: UUID,
        user_id: UUID | None,
        owner_token: str,
        metadata: dict[str, object] | None = None,
    ) -> LockAcquireResult:
        now = _utcnow()
        self._delete_stale_for_conversation(db, conversation_id=conversation_id, now=now)

        lock = ConversationLock(
            conversation_id=conversation_id,
            resource_id=conversation_id,
            locked_by=user_id,
            owner_token=owner_token,
            locked_at=now,
            last_heartbeat_at=now,
            expires_at=now + timedelta(seconds=LOCK_TTL_SECONDS),
            stale_after_seconds=LOCK_TTL_SECONDS,
            metadata_json=metadata or {},
        )
        db.add(lock)
        try:
            db.commit()
            return LockAcquireResult(
                acquired=True,
                state=LockState(
                    conversation_id=conversation_id,
                    is_busy=True,
                    locked_by=user_id,
                    reason="assistant_turn_in_progress",
                    owner_token=owner_token,
                ),
            )
        except IntegrityError:
            db.rollback()

        existing = self._get_lock(db, conversation_id=conversation_id)
        now = _utcnow()
        if existing is not None and _is_stale(existing, now):
            self._delete_stale_for_conversation(db, conversation_id=conversation_id, now=now)
            return self.acquire(
                db,
                conversation_id=conversation_id,
                user_id=user_id,
                owner_token=owner_token,
                metadata=metadata,
            )

        return LockAcquireResult(
            acquired=False,
            state=LockState(
                conversation_id=conversation_id,
                is_busy=True,
                locked_by=existing.locked_by if existing is not None else None,
                reason="assistant_turn_in_progress",
                owner_token=existing.owner_token if existing is not None else None,
            ),
        )

    def heartbeat(self, db: Session, *, conversation_id: UUID, owner_token: str) -> bool:
        now = _utcnow()
        result = db.execute(
            update(ConversationLock)
            .where(
                ConversationLock.conversation_id == conversation_id,
                ConversationLock.owner_token == owner_token,
            )
            .values(
                last_heartbeat_at=now,
                expires_at=now + timedelta(seconds=LOCK_TTL_SECONDS),
            )
        )
        db.commit()
        return (result.rowcount or 0) > 0

    def release(self, db: Session, *, conversation_id: UUID, owner_token: str) -> bool:
        result = db.execute(
            delete(ConversationLock).where(
                ConversationLock.conversation_id == conversation_id,
                ConversationLock.owner_token == owner_token,
            )
        )
        db.commit()
        return (result.rowcount or 0) > 0

    def get_state(self, db: Session, *, conversation_id: UUID) -> LockState:
        now = _utcnow()
        lock = self._get_lock(db, conversation_id=conversation_id)
        if lock is None:
            return LockState(
                conversation_id=conversation_id,
                is_busy=False,
                locked_by=None,
                reason="idle",
                owner_token=None,
            )

        if _is_stale(lock, now):
            self._delete_stale_for_conversation(db, conversation_id=conversation_id, now=now)
            return LockState(
                conversation_id=conversation_id,
                is_busy=False,
                locked_by=None,
                reason="idle",
                owner_token=None,
            )

        return LockState(
            conversation_id=conversation_id,
            is_busy=True,
            locked_by=lock.locked_by,
            reason="assistant_turn_in_progress",
            owner_token=lock.owner_token,
        )

    def _get_lock(self, db: Session, *, conversation_id: UUID) -> ConversationLock | None:
        return db.execute(
            select(ConversationLock).where(ConversationLock.conversation_id == conversation_id)
        ).scalar_one_or_none()

    def _delete_stale_for_conversation(self, db: Session, *, conversation_id: UUID, now: datetime) -> int:
        lock = self._get_lock(db, conversation_id=conversation_id)
        if lock is None or not _is_stale(lock, now):
            return 0

        result = db.execute(delete(ConversationLock).where(ConversationLock.id == lock.id))
        db.commit()
        return result.rowcount or 0


conversation_lock_service = ConversationLockService()
