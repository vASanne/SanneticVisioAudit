"""API key ids and secret hashes.

The secret is random, shown once, and stored only as HMAC-SHA256 with the
server pepper from ``API_KEY_PEPPER``. Comparison uses ``hmac.compare_digest``.
Argon2 is the right tool for human passwords. These secrets are 256-bit tokens
checked on every request, so a slow password hash would turn a known key id
into a CPU exhaustion knob. A peppered HMAC is not reversible from a database
copy, and the pepper never has a default in code.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets

from app.core.config import get_settings

KEY_PREFIX = "vak_"
SECRET_PREFIX = "vas_"
_KEY_ID = re.compile(r"^vak_[A-Za-z0-9_-]{16,64}$")
_MAX_SECRET_LENGTH = 200
_DUMMY_HASH = "0" * 64


class ApiKeyNotConfigured(RuntimeError):
    """API_KEY_PEPPER is missing or too short to hash a secret."""


def pepper_bytes() -> bytes:
    value = get_settings().api_key_pepper.strip()
    if len(value) < 32:
        raise ApiKeyNotConfigured("API_KEY_PEPPER must be at least 32 characters")
    return value.encode("utf-8")


def generate_key_id() -> str:
    return KEY_PREFIX + secrets.token_urlsafe(18)


def generate_secret() -> str:
    return SECRET_PREFIX + secrets.token_urlsafe(32)


def is_key_id(value: str) -> bool:
    return bool(_KEY_ID.fullmatch(value))


def secret_hash(secret: str) -> str:
    """Return the hex HMAC stored in the database. The secret is not recoverable."""

    if not isinstance(secret, str) or not secret or len(secret) > _MAX_SECRET_LENGTH:
        raise ValueError("secret length is not allowed")
    digest = hmac.new(pepper_bytes(), secret.encode("utf-8"), hashlib.sha256)
    return digest.hexdigest()


def secret_matches(secret: str, stored: str) -> bool:
    """Constant-time check. A malformed stored hash still runs one compare."""

    if not isinstance(secret, str) or not secret or len(secret) > _MAX_SECRET_LENGTH:
        hmac.compare_digest(_DUMMY_HASH, _DUMMY_HASH)
        return False
    digest = secret_hash(secret)
    if not isinstance(stored, str) or len(stored) != len(digest):
        hmac.compare_digest(digest, _DUMMY_HASH)
        return False
    return hmac.compare_digest(digest, stored)


def rate_identity(presented_key: str) -> str:
    """Redis-key material. Invalid headers are hashed so they are not stored raw."""

    if is_key_id(presented_key):
        return presented_key
    if not presented_key:
        return "missing"
    # Not a password. An unrecognized key id is reduced to a short digest so the
    # raw header is neither a Redis key nor a usage-log value.
    digest = hashlib.sha256(presented_key.encode("utf-8", errors="replace")).hexdigest()[:16]  # codeql[py/weak-sensitive-data-hashing]
    return f"invalid:{digest}"


def event_key_id(presented_key: str) -> str:
    """Value safe to store in the usage log. Never the secret."""

    if is_key_id(presented_key):
        return presented_key
    if not presented_key:
        return ""
    return rate_identity(presented_key)[:80]
