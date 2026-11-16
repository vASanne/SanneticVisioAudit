"""Password and token helpers."""

from uuid import uuid4

from app.core.config import get_settings
from app.core.security import AuthUser, auth_enabled, hash_password, issue_token, parse_token, verify_password


def test_password_roundtrip_and_token() -> None:
    encoded = hash_password("geheim-123")
    assert verify_password("geheim-123", encoded)
    assert not verify_password("wrong", encoded)
    user = AuthUser(id=uuid4(), email="a@example.com", name="Ada", is_admin=True)
    token = issue_token(user, ttl_seconds=60)
    parsed = parse_token(token)
    assert parsed is not None
    assert parsed.email == "a@example.com"
    assert parsed.is_admin is True


def test_auth_enabled_needs_usable_agency_login_or_secret(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "auth_secret", "")
    monkeypatch.setattr(settings, "agency_email", "admin@example.com")
    monkeypatch.setattr(settings, "agency_password", "")
    assert auth_enabled() is False
    monkeypatch.setattr(settings, "agency_password", "geheim-123")
    assert auth_enabled() is True
    monkeypatch.setattr(settings, "agency_email", "")
    monkeypatch.setattr(settings, "agency_password", "")
    monkeypatch.setattr(settings, "auth_secret", "signing-secret")
    assert auth_enabled() is True
