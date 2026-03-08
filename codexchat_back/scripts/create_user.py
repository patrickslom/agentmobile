"""CLI user creation utility for SSH/bootstrap workflows."""

from __future__ import annotations

import argparse
import getpass
import json
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.models import User
from app.db.session import SessionLocal
from app.domains.auth.password import hash_password


def _normalize_role(raw_role: str) -> str:
    role = raw_role.strip().lower()
    if role not in {"user", "admin"}:
        raise ValueError("role must be one of: user, admin")
    return role


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a CodexChat user.")
    parser.add_argument("--email", help="User email")
    parser.add_argument("--password", help="User password")
    parser.add_argument("--role", default="user", help="Role: user|admin (default: user)")
    parser.add_argument(
        "--force-password-reset",
        dest="force_password_reset",
        action="store_true",
        default=True,
        help="Force password reset on first login (default: enabled)",
    )
    parser.add_argument(
        "--no-force-password-reset",
        dest="force_password_reset",
        action="store_false",
        help="Disable forced password reset on first login",
    )
    return parser.parse_args()


def _interactive_fallback(args: argparse.Namespace) -> argparse.Namespace:
    needs_prompt = not args.email or not args.password
    if not needs_prompt:
        return args

    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        missing = []
        if not args.email:
            missing.append("--email")
        if not args.password:
            missing.append("--password")
        raise ValueError(
            f"missing required flags in non-interactive mode: {', '.join(missing)}"
        )

    if not args.email:
        args.email = input("Email: ").strip()
    if not args.password:
        args.password = getpass.getpass("Password: ").strip()
    return args


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


def main() -> int:
    try:
        args = _interactive_fallback(_parse_args())
        email = (args.email or "").strip().lower()
        password = (args.password or "").strip()
        if len(email) < 3:
            raise ValueError("email must be at least 3 characters")
        if len(password) < 8:
            raise ValueError("password must be at least 8 characters")
        role = _normalize_role(args.role)
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1

    user_payload: dict[str, object]
    with SessionLocal() as db:
        existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if existing is not None:
            print(json.dumps({"ok": False, "error": "user already exists"}))
            return 1

        user = User(
            email=email,
            password_hash=hash_password(password),
            display_name=_next_available_display_name(db, email),
            role=role,
            is_active=True,
            force_password_reset=args.force_password_reset,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_payload = {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "force_password_reset": user.force_password_reset,
        }
    print(
        json.dumps(
            {
                "ok": True,
                "user": user_payload,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
