"""Password and token helpers."""

import hashlib
from uuid import uuid4

import pytest

from app.core.config import get_settings
from app.core.security import (
    AuthNotConfigured,
    AuthUser,
    auth_enabled,
    hash_password,
    issue_token,
    parse_token,
    verify_password,
)

_SECRET = "x" * 32


def test_password_roundtrip_and_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "auth_secret", _SECRET)
    encoded = hash_password("geheim-123")
    assert encoded.startswith("$argon2")
    assert verify_password("geheim-123", encoded)
    assert not verify_password("wrong", encoded)
    user = AuthUser(id=uuid4(), email="a@example.com", name="Ada", is_admin=True)
    token = issue_token(user, ttl_seconds=60)
    parsed = parse_token(token)
    assert parsed is not None
    assert parsed.email == "a@example.com"
    assert parsed.is_admin is True
    assert parse_token(token + "tampered") is None
    monkeypatch.setattr(get_settings(), "auth_secret", "too-short")
    with pytest.raises(AuthNotConfigured):
        issue_token(user)


def test_legacy_pbkdf2_verifies_only_with_the_original_parameters() -> None:
    salt = bytes.fromhex("11" * 16)
    digest = hashlib.pbkdf2_hmac("sha256", b"geheim-123", salt, 260_000)
    encoded = f"pbkdf2_sha256$260000${salt.hex()}${digest.hex()}"
    assert verify_password("geheim-123", encoded)
    assert not verify_password("wrong", encoded)
    hostile = f"pbkdf2_sha256$1${salt.hex()}${digest.hex()}"
    assert not verify_password("geheim-123", hostile)


def test_log_redaction_strips_session_cookies() -> None:
    from app.core.logging import _redact, _redact_text

    cleaned = _redact_text("visioaudit_session=abc.def.ghi; visioaudit_csrf=secrettoken")
    assert "abc.def" not in cleaned
    assert "secrettoken" not in cleaned
    assert "visioaudit_session=[redacted]" in cleaned
    secret = "vas_example_replace_me"
    header = _redact_text(f"X-Api-Secret: {secret}")
    assert secret not in header
    event = _redact(None, None, {"api_secret": secret, "key_id": "vak_example"})
    assert event["api_secret"] == "[redacted]"
    assert event["key_id"] == "vak_example"


def test_samesite_none_is_rejected() -> None:
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(cookie_samesite="none")


def test_auth_is_required_unless_explicitly_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "auth_disabled", False)
    monkeypatch.setattr(settings, "auth_secret", "")
    monkeypatch.setattr(settings, "agency_password", "")
    assert auth_enabled() is True
    monkeypatch.setattr(settings, "auth_disabled", True)
    assert auth_enabled() is False
