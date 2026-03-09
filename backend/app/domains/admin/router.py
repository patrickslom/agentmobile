from __future__ import annotations

import secrets
import string
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import Session as AuthSession
from app.db.models import User
from app.db.session import get_db
from app.domains.auth.dependencies import get_current_admin_user
from app.domains.auth.password import hash_password

router = APIRouter(prefix="/admin", tags=["admin"])


class AdminUserCreateRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=4096)
    role: str = Field(default="user")
    force_password_reset: bool = Field(default=True)


class AdminUserPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str | None = Field(default=None)
    is_active: bool | None = Field(default=None)
    force_password_reset: bool | None = Field(default=None)


class AdminUserResponse(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool
    force_password_reset: bool
    created_at: datetime
    updated_at: datetime


class AdminTemporaryPasswordResetResponse(BaseModel):
    user: AdminUserResponse
    temporary_password: str


def _normalize_display_name_from_email(email: str) -> str:
    local_part = email.split("@", 1)[0].strip().lower()
    normalized = "".join(ch for ch in local_part if ch.isalnum() or ch in {"_", "-", "."})
    if not normalized:
        normalized = "user"
    if len(normalized) > 64:
        normalized = normalized[:64]
    return normalized


def _next_available_display_name(db: Session, email: str) -> str:
    base_name = _normalize_display_name_from_email(email)
    candidate = base_name
    suffix = 2
    while True:
        existing = db.execute(select(User).where(User.display_name == candidate)).scalar_one_or_none()
        if existing is None:
            return candidate
        candidate = f"{base_name}-{suffix}"
        if len(candidate) > 64:
            candidate = candidate[:64]
            if "-" in candidate:
                candidate = candidate.rsplit("-", 1)[0]
                if not candidate:
                    candidate = "user"
        suffix += 1


def _validate_role(role: str) -> str:
    normalized = role.strip().lower()
    if normalized not in {"user", "admin"}:
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message="Role must be one of: user, admin",
            details={},
        )
    return normalized


def _to_response(user: User) -> AdminUserResponse:
    return AdminUserResponse(
        id=str(user.id),
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        force_password_reset=user.force_password_reset,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _generate_temporary_password(length: int = 20) -> str:
    if length < 12:
        length = 12
    alphabet = string.ascii_letters + string.digits
    required = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
    ]
    remaining = [secrets.choice(alphabet) for _ in range(length - len(required))]
    chars = required + remaining
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


@router.post("/users")
def create_user(
    payload: AdminUserCreateRequest,
    _: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> dict[str, AdminUserResponse]:
    email = payload.email.strip().lower()
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing is not None:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            code="USER_ALREADY_EXISTS",
            message="User with this email already exists",
            details={},
        )

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        role=_validate_role(payload.role),
        display_name=_next_available_display_name(db, email),
        is_active=True,
        force_password_reset=payload.force_password_reset,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"user": _to_response(user)}


@router.get("/users")
def list_users(
    _: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> dict[str, list[AdminUserResponse]]:
    users = db.execute(select(User).order_by(User.created_at.asc())).scalars().all()
    return {"users": [_to_response(user) for user in users]}


@router.patch("/users/{user_id}")
def patch_user(
    user_id: UUID,
    payload: AdminUserPatchRequest,
    _: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> dict[str, AdminUserResponse]:
    user = db.get(User, user_id)
    if user is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="User not found",
            details={},
        )

    has_changes = False
    if payload.role is not None:
        user.role = _validate_role(payload.role)
        has_changes = True
    if payload.is_active is not None:
        user.is_active = payload.is_active
        has_changes = True
    if payload.force_password_reset is not None:
        user.force_password_reset = payload.force_password_reset
        has_changes = True

    if not has_changes:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="BAD_REQUEST",
            message="No updates were provided",
            details={},
        )

    user.updated_at = datetime.now(tz=UTC)
    db.commit()
    db.refresh(user)
    return {"user": _to_response(user)}


@router.post("/users/{user_id}/temporary-password")
def reset_user_temporary_password(
    user_id: UUID,
    _: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> AdminTemporaryPasswordResetResponse:
    user = db.get(User, user_id)
    if user is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message="User not found",
            details={},
        )

    temporary_password = _generate_temporary_password()
    now = datetime.now(tz=UTC)

    user.password_hash = hash_password(temporary_password)
    user.force_password_reset = True
    user.updated_at = now

    db.execute(
        update(AuthSession)
        .where(
            AuthSession.user_id == user.id,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )

    db.commit()
    db.refresh(user)

    return AdminTemporaryPasswordResetResponse(
        user=_to_response(user),
        temporary_password=temporary_password,
    )
