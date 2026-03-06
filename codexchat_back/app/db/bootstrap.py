"""Bootstrap seed helpers for first-run database defaults."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Settings, User
from app.domains.auth.password import hash_password


def seed_defaults(db: Session) -> dict[str, bool]:
    """Seed default settings row and optional first admin user idempotently."""
    settings = get_settings()
    seeded_settings = False
    seeded_admin = False

    settings_row = db.get(Settings, 1)
    if settings_row is None:
        db.add(Settings(id=1))
        seeded_settings = True

    admin_email = (settings.admin_email or "").strip().lower()
    admin_password_hash = (settings.admin_password_hash or "").strip()
    admin_password = settings.admin_password or ""
    if admin_email and (admin_password_hash or admin_password):
        existing_admin = db.execute(select(User).where(User.email == admin_email)).scalar_one_or_none()
        if existing_admin is None:
            password_hash = admin_password_hash or hash_password(admin_password)
            db.add(
                User(
                    email=admin_email,
                    password_hash=password_hash,
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
