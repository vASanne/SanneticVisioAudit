"""Cookie session, CSRF rejection, and logout."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.security import AuthUser, issue_token
from app.main import app
from app.models import User

_SECRET = "s" * 32


def _csrf(client: TestClient) -> str:
    response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    token = response.json()["csrf_token"]
    assert isinstance(token, str) and len(token) >= 32
    issued = "; ".join(response.headers.get_list("set-cookie")).lower()
    assert "visioaudit_csrf=" in issued
    assert "httponly" in issued
    assert "secure" in issued
    assert "samesite=lax" in issued
    return token


def test_request_cookie_is_not_copied_into_set_cookie() -> None:
    planted = "a" * 43
    with TestClient(app, base_url="https://testserver") as client:
        client.cookies.set("visioaudit_csrf", planted)
        response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    assert response.json()["csrf_token"] == planted
    assert all(planted not in item for item in response.headers.get_list("set-cookie"))


def test_state_change_without_csrf_is_rejected() -> None:
    with TestClient(app, base_url="https://testserver") as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "person@example.com", "password": "longenough"},
        )
    assert response.status_code == 403
    assert response.json()["detail"] == "CSRF-Token fehlt oder ist ungültig."


def test_mismatched_csrf_is_rejected() -> None:
    with TestClient(app, base_url="https://testserver") as client:
        _csrf(client)
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "person@example.com", "password": "longenough"},
            headers={"X-CSRF-Token": "a" * 43},
        )
    assert response.status_code == 403
    assert response.json()["detail"] == "CSRF-Token fehlt oder ist ungültig."


def test_bearer_header_is_not_a_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "auth_secret", _SECRET)
    monkeypatch.setattr(get_settings(), "auth_disabled", False)
    token = issue_token(AuthUser(id=uuid4(), email="a@example.com", name="Ada", is_admin=True))
    with TestClient(app, base_url="https://testserver") as client:
        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_login_sets_httponly_cookie_and_logout_clears_it(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.__table__.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    monkeypatch.setattr("app.core.database.SessionLocal", factory)
    settings = get_settings()
    monkeypatch.setattr(settings, "auth_secret", _SECRET)
    monkeypatch.setattr(settings, "auth_disabled", False)
    monkeypatch.setattr(settings, "agency_email", "admin@example.com")
    monkeypatch.setattr(settings, "agency_password", "longenough-password")
    monkeypatch.setattr(settings, "agency_name", "Agency")
    monkeypatch.setattr(settings, "cookie_secure", True)
    monkeypatch.setattr(settings, "cookie_samesite", "lax")

    with TestClient(app, base_url="https://testserver") as client:
        csrf = _csrf(client)
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "longenough-password"},
            headers={"X-CSRF-Token": csrf, "Origin": "http://127.0.0.1:3000"},
        )
        assert login.status_code == 200
        body = login.json()
        assert "access_token" not in body
        assert "eyJ" not in login.text
        assert body["email"] == "admin@example.com"
        assert body["is_admin"] is True
        session = next(item for item in login.headers.get_list("set-cookie") if item.startswith("visioaudit_session="))
        folded = session.lower()
        assert "httponly" in folded
        assert "secure" in folded
        assert "samesite=lax" in folded
        status = client.get("/api/v1/auth/status")
        assert status.json()["authenticated"] is True
        logged_out = client.post(
            "/api/v1/auth/logout",
            headers={"X-CSRF-Token": body["csrf_token"], "Origin": "http://127.0.0.1:3000"},
        )
        assert logged_out.status_code == 200
        cleared = next(item for item in logged_out.headers.get_list("set-cookie") if "visioaudit_session=" in item)
        assert "max-age=0" in cleared.lower()
        after = client.get("/api/v1/auth/status")
        assert after.json()["authenticated"] is False


def test_credentials_are_limited_to_the_configured_origin() -> None:
    with TestClient(app, base_url="https://testserver") as client:
        allowed = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://127.0.0.1:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,x-csrf-token",
            },
        )
        assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"
        assert allowed.headers["access-control-allow-credentials"] == "true"
        assert allowed.headers["access-control-allow-origin"] != "*"
        blocked = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert blocked.headers.get("access-control-allow-origin") in {None, ""}
