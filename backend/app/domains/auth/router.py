from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.models import User
from app.db.session import get_db
from app.domains.auth.dependencies import get_current_user
from app.domains.auth.password import hash_password
from app.domains.auth.lockout import lockout_service
from app.domains.auth.password import verify_password
from app.domains.auth.session import session_manager

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

GENERIC_AUTH_MESSAGE = "Invalid email or password"


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=4096)


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=4096)


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    force_password_reset: bool


def _resolve_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


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


def _set_auth_cookies(response: Response, *, session_cookie: str, csrf_token: str, expires_at: datetime) -> None:
    response.set_cookie(
        key=session_manager.session_cookie_name,
        value=session_cookie,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
        expires=expires_at,
    )
    response.set_cookie(
        key=session_manager.csrf_cookie_name,
        value=csrf_token,
        httponly=False,
        secure=True,
        samesite="lax",
        path="/",
        expires=expires_at,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        key=session_manager.session_cookie_name,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    response.delete_cookie(
        key=session_manager.csrf_cookie_name,
        httponly=False,
        secure=True,
        samesite="lax",
        path="/",
    )


def _lockout_details(ban_until: datetime) -> dict[str, object]:
    now = datetime.now(tz=UTC)
    retry_after_seconds = max(int((ban_until - now).total_seconds()), 1)
    return {
        "retry_after_seconds": retry_after_seconds,
        "retry_after_minutes": max((retry_after_seconds + 59) // 60, 1),
        "ban_until": ban_until.isoformat(),
    }


@router.post("/login")
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> dict[str, UserResponse]:
    email = payload.email.strip().lower()
    client_ip = _resolve_client_ip(request)
    ban_until = lockout_service.is_locked(db, email=email, ip=client_ip)
    if ban_until is not None:
        raise AppError(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="AUTH_LOCKED",
            message=GENERIC_AUTH_MESSAGE,
            details=_lockout_details(ban_until),
        )

    user = db.execute(select(User).where(User.email == email, User.is_active.is_(True))).scalar_one_or_none()
    is_valid_password = bool(user and verify_password(payload.password, user.password_hash))
    if not is_valid_password:
        updated_ban_until = lockout_service.register_failure(db, email=email, ip=client_ip)
        status_code = status.HTTP_429_TOO_MANY_REQUESTS if updated_ban_until else status.HTTP_401_UNAUTHORIZED
        error_code = "AUTH_LOCKED" if updated_ban_until else "AUTH_INVALID"
        details = _lockout_details(updated_ban_until) if updated_ban_until else {}
        raise AppError(
            status_code=status_code,
            code=error_code,
            message=GENERIC_AUTH_MESSAGE,
            details=details,
        )

    lockout_service.clear_failures(db, email=email, ip=client_ip)
    auth_session = session_manager.create_session(db, user_id=user.id)
    _set_auth_cookies(
        response,
        session_cookie=auth_session.cookie_value,
        csrf_token=session_manager.csrf_for_session(auth_session.session_id),
        expires_at=auth_session.expires_at,
    )
    return {
        "user": UserResponse(
            id=str(user.id),
            email=user.email,
            role=user.role,
            force_password_reset=user.force_password_reset,
        )
    }


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> dict[str, str]:
    raw_cookie = request.cookies.get(session_manager.session_cookie_name)
    session_id = session_manager.parse_cookie_value(raw_cookie)
    if session_id:
        session_manager.revoke_session(db, session_id=session_id)
    _clear_auth_cookies(response)
    return {"status": "ok"}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)) -> dict[str, UserResponse]:
    return {
        "user": UserResponse(
            id=str(current_user.id),
            email=current_user.email,
            role=current_user.role,
            force_password_reset=current_user.force_password_reset,
        )
    }


@router.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> dict[str, UserResponse]:
    if not settings.enable_public_registration:
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code="REGISTRATION_DISABLED",
            message="Public registration is disabled",
            details={},
        )

    email = payload.email.strip().lower()
    existing_user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing_user is not None:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            code="USER_ALREADY_EXISTS",
            message="User with this email already exists",
            details={},
        )

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        role="user",
        display_name=_next_available_display_name(db, email),
        is_active=True,
        force_password_reset=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "user": UserResponse(
            id=str(user.id),
            email=user.email,
            role=user.role,
            force_password_reset=user.force_password_reset,
        )
    }
