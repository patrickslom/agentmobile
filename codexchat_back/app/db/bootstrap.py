"""Bootstrap seed helpers for first-run database defaults."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Settings, User
from app.domains.auth.password import hash_password


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


def seed_defaults(db: Session) -> dict[str, bool]:
    """Seed default settings row and optional first admin user idempotently."""
    settings = get_settings()
    seeded_settings = False
    seeded_admin = False

    settings_row = db.get(Settings, 1)
    if settings_row is None:
        db.add(Settings(id=1))
        seeded_settings = True

    admin_email = (settings.admin_bootstrap_email or settings.admin_email or "").strip().lower()
    admin_password_hash = (
        settings.admin_bootstrap_password_hash or settings.admin_password_hash or ""
    ).strip()
    admin_password = settings.admin_bootstrap_password or settings.admin_password or ""
    if admin_email and (admin_password_hash or admin_password):
        existing_admin = db.execute(select(User).where(User.email == admin_email)).scalar_one_or_none()
        if existing_admin is None:
            password_hash = admin_password_hash or hash_password(admin_password)
            db.add(
                User(
                    email=admin_email,
                    password_hash=password_hash,
                    display_name=_next_available_display_name(db, admin_email),
                    role="admin",
                    is_active=True,
                    force_password_reset=False,
                )
            )
            seeded_admin = True

    if seeded_settings or seeded_admin:
        db.commit()

    return {
        "seeded_settings": seeded_settings,
        "seeded_admin": seeded_admin,
    }
