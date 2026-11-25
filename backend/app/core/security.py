"""Password hashing and signed session tokens.

Passwords use the argon2-cffi library. Tokens are HMAC JWTs from PyJWT.
Existing pbkdf2 hashes still verify so older rows can sign in once and are
then replaced with an argon2 hash. New passwords are never stored with the
legacy scheme.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from jwt import InvalidTokenError

from app.core.config import get_settings

_HASHER = PasswordHasher()
_LEGACY_ITERATIONS = 260_000
_MIN_SECRET_LENGTH = 32
# Verified once at import so a missing account takes about as long as a real check.
_DUMMY_HASH = _HASHER.hash("visioaudit-dummy-password")


@dataclass(frozen=True)
class AuthUser:
    id: UUID
    email: str
    name: str
    is_admin: bool


class AuthNotConfigured(RuntimeError):
    """AUTH_SECRET is missing or too short to sign a session."""


def hash_password(password: str) -> str:
    if not isinstance(password, str) or not 8 <= len(password) <= 200:
        raise ValueError("password length is not allowed")
    return _HASHER.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    if not isinstance(password, str) or not password or len(password) > 200:
        return False
    if not encoded:
        _consume_dummy(password)
        return False
    if encoded.startswith("$argon2"):
        return _verify_argon2(password, encoded)
    if encoded.startswith("pbkdf2_sha256$"):
        return _verify_legacy_pbkdf2(password, encoded)
    _consume_dummy(password)
    return False


def needs_rehash(encoded: str) -> bool:
    """True when a successful login should store a new argon2 hash."""

    if not encoded.startswith("$argon2"):
        return True
    return _HASHER.check_needs_rehash(encoded)


def issue_token(user: AuthUser, *, ttl_seconds: int = 60 * 60 * 12) -> str:
    secret = _secret()
    now = int(time.time())
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "name": user.name,
        "admin": user.is_admin,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    if isinstance(token, bytes):
        return token.decode("ascii")
    return token


def parse_token(token: str) -> AuthUser | None:
    """Return the session claims. Callers must still load the user from the database."""

    try:
        secret = _secret()
    except AuthNotConfigured:
        return None
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"require": ["exp", "sub", "iat"]},
        )
    except InvalidTokenError:
        return None
    try:
        return AuthUser(
            id=UUID(str(payload["sub"])),
            email=str(payload["email"]),
            name=str(payload["name"]),
            is_admin=bool(payload.get("admin")),
        )
    except (KeyError, ValueError, TypeError):
        return None


def auth_enabled() -> bool:
    """Auth is required unless AUTH_DISABLED is explicitly set."""

    return not get_settings().auth_disabled


def _secret() -> str:
    value = get_settings().auth_secret.strip()
    if len(value) < _MIN_SECRET_LENGTH:
        raise AuthNotConfigured("AUTH_SECRET must be at least 32 characters")
    return value


def _verify_argon2(password: str, encoded: str) -> bool:
    try:
        return _HASHER.verify(encoded, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def _verify_legacy_pbkdf2(password: str, encoded: str) -> bool:
    try:
        scheme, iterations_raw, salt_hex, digest_hex = encoded.split("$", 3)
    except ValueError:
        return False
    if scheme != "pbkdf2_sha256":
        return False
    try:
        iterations = int(iterations_raw)
    except ValueError:
        return False
    # Only the parameter this application used to write. A stored hash cannot
    # pick a huge iteration count and stall the login worker.
    if iterations != _LEGACY_ITERATIONS:
        return False
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except ValueError:
        return False
    if len(salt) < 16 or len(expected) != 32:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(digest, expected)


def _consume_dummy(password: str) -> None:
    try:
        _HASHER.verify(_DUMMY_HASH, password)
    except (VerifyMismatchError, InvalidHashError):
        return
