from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_PASSWORD_HASHER = PasswordHasher()


def ensure_password_backend() -> None:
    """Force import-time startup failure when argon2-cffi is unavailable."""
    _ = _PASSWORD_HASHER


def hash_password(password: str) -> str:
    return _PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _PASSWORD_HASHER.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False
