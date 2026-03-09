from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import User
from app.db.session import get_db
from app.domains.auth.session import session_manager


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    auth_session = session_manager.resolve_session(
        db,
        cookie_value=request.cookies.get(session_manager.session_cookie_name),
    )
    if auth_session is None:
        raise AppError(
            status_code=401,
            code="AUTH_INVALID",
            message="Authentication required",
            details={},
        )

    user = db.execute(
        select(User).where(User.id == auth_session.user_id, User.is_active.is_(True))
    ).scalar_one_or_none()
    if user is None:
        raise AppError(
            status_code=401,
            code="AUTH_INVALID",
            message="Authentication required",
            details={},
        )
    return user


def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "admin":
        raise AppError(
            status_code=403,
            code="FORBIDDEN",
            message="Admin access required",
            details={},
        )
    return current_user
