"""Password hashing and signed session tokens."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from uuid import UUID

from app.core.config import get_settings

_ITERATIONS = 260_000


@dataclass(frozen=True)
class AuthUser:
    id: UUID
    email: str
    name: str
    is_admin: bool


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iterations, salt_hex, digest_hex = encoded.split("$", 3)
    except ValueError:
        return False
    if scheme != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        int(iterations),
    )
    return hmac.compare_digest(digest.hex(), digest_hex)


def issue_token(user: AuthUser, *, ttl_seconds: int = 60 * 60 * 12) -> str:
    secret = _secret()
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "name": user.name,
        "admin": user.is_admin,
        "exp": int(time.time()) + ttl_seconds,
    }
    body = urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("ascii").rstrip("=")
    signature = hmac.new(secret, body.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def parse_token(token: str) -> AuthUser | None:
    try:
        body, signature = token.split(".", 1)
    except ValueError:
        return None
    secret = _secret()
    expected = hmac.new(secret, body.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return None
    padding = "=" * (-len(body) % 4)
    try:
        payload = json.loads(urlsafe_b64decode(body + padding).decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
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
    """Auth is on when a signing secret exists, or agency login can be bootstrapped."""

    settings = get_settings()
    if settings.auth_secret.strip():
        return True
    return bool(settings.agency_email.strip() and settings.agency_password.strip())


def _secret() -> bytes:
    settings = get_settings()
    value = settings.auth_secret.strip() or settings.agency_password.strip() or "REDACTED"
    return value.encode("utf-8")
