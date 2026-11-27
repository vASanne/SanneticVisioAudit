"""Agent API: key plus secret, tenant isolation, limits, SSRF, and stored results."""

from __future__ import annotations

import socket
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
import redis
from app.core import rate_limit
from app.core.api_keys import secret_hash, secret_matches
from app.core.config import get_settings
from app.core.security import hash_password
from app.crawler.safety import assert_public_url
from app.main import app, create_app
from app.models import ApiKey, ApiKeyEvent, Audit, Base, Client, Issue, Membership, Score, User
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

_PEPPER = "p" * 32
_AUTH = "s" * 32


def _public(_host: str, _port: object, *_args: object, **_kwargs: object) -> list[tuple[object, ...]]:
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]


def _private(_host: str, _port: object, *_args: object, **_kwargs: object) -> list[tuple[object, ...]]:
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.1.1.1", 0))]


def _assert_public(url: str) -> None:
    assert_public_url(url, resolver=_public)


class _DownRedis:
    def eval(self, *_args: object, **_kwargs: object) -> int:
        raise redis.RedisError("unavailable")


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection: object, _record: object) -> None:
        connection: Any = dbapi_connection
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker[Session](bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    monkeypatch.setattr("app.core.database.SessionLocal", factory)
    settings = get_settings()
    monkeypatch.setattr(settings, "api_key_pepper", _PEPPER)
    monkeypatch.setattr(settings, "auth_secret", _AUTH)
    monkeypatch.setattr(settings, "auth_disabled", False)
    monkeypatch.setattr(settings, "agency_email", "")
    monkeypatch.setattr(settings, "agency_password", "")
    monkeypatch.setattr(settings, "cookie_secure", True)
    monkeypatch.setattr("app.services.agent_audits.run_audit_task.delay", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("app.services.audit_service.assert_public_url", _assert_public)
    with TestClient(app, base_url="https://testserver") as client:
        yield client, factory


def _seed(factory: sessionmaker[Session]) -> dict[str, UUID]:
    db = factory()
    admin = User(
        email="admin@example.com",
        name="Admin",
        password_hash=hash_password("longenough-password"),
        is_admin=True,
        is_api_user=False,
    )
    member = User(
        email="member@example.com",
        name="Member",
        password_hash=hash_password("longenough-password"),
        is_admin=False,
        is_api_user=False,
    )
    north = Client(name="North", domain="example.com", settings={})
    south = Client(name="South", domain="example.org", settings={})
    db.add_all([admin, member, north, south])
    db.flush()
    db.add(Membership(user_id=member.id, client_id=north.id, role="member"))
    db.commit()
    ids = {"admin": admin.id, "member": member.id, "north": north.id, "south": south.id}
    db.close()
    return ids


def _login(client: TestClient, email: str, password: str) -> str:
    token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
        headers={"X-CSRF-Token": token, "Origin": "http://127.0.0.1:3000"},
    )
    assert response.status_code == 200, response.text
    token = response.json()["csrf_token"]
    if not isinstance(token, str):
        raise AssertionError("csrf token missing")
    return token


def _create_api_user(
    client: TestClient, csrf: str, client_id: UUID, *, scopes: list[str] | None = None
) -> dict[str, str]:
    body: dict[str, object] = {
        "name": "Nightly",
        "is_api_user": True,
        "is_admin": False,
        "client_ids": [str(client_id)],
    }
    if scopes is not None:
        body["scopes"] = scopes
    response = client.post(
        "/api/v1/users",
        json=body,
        headers={"X-CSRF-Token": csrf, "Origin": "http://127.0.0.1:3000"},
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["is_api_user"] is True
    assert payload["api_credential"]["secret"]
    return {
        "user_id": payload["id"],
        "key_row_id": payload["api_keys"][0]["id"],
        "key_id": payload["api_credential"]["key_id"],
        "secret": payload["api_credential"]["secret"],
    }


def _agent(key_id: str, secret: str) -> dict[str, str]:
    return {"X-Api-Key": key_id, "X-Api-Secret": secret}


def test_secret_hash_is_peppered_and_compared_in_constant_time(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "api_key_pepper", _PEPPER)
    stored = secret_hash("vas_example_replace_me")
    assert stored != "vas_example_replace_me"
    assert secret_matches("vas_example_replace_me", stored)
    assert secret_matches("vas_other_value_here", stored) is False
    monkeypatch.setattr(get_settings(), "api_key_pepper", "q" * 32)
    assert secret_matches("vas_example_replace_me", stored) is False


def test_missing_wrong_revoked_and_expired_keys_are_rejected(api: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, factory = api
    ids = _seed(factory)
    csrf = _login(client, "admin@example.com", "longenough-password")
    created = _create_api_user(client, csrf, ids["north"])
    secret = created["secret"]

    missing = client.get("/api/v1/agent/audits")
    assert missing.status_code == 401
    wrong = client.get("/api/v1/agent/audits", headers=_agent(created["key_id"], "vas_wrong_secret_value"))
    assert wrong.status_code == 401
    assert secret not in wrong.text

    db = factory()
    events = db.scalars(select(ApiKeyEvent)).all()
    blob = " ".join(f"{row.key_id} {row.action} {row.path}" for row in events)
    assert secret not in blob
    assert "vas_wrong_secret_value" not in blob
    db.close()

    revoked = client.post(
        f"/api/v1/api-keys/{created['key_row_id']}/revoke",
        headers={"X-CSRF-Token": csrf, "Origin": "http://127.0.0.1:3000"},
    )
    assert revoked.status_code == 200
    assert "secret" not in revoked.json()
    assert client.get("/api/v1/agent/audits", headers=_agent(created["key_id"], secret)).status_code == 401

    fresh = _create_api_user(client, csrf, ids["north"])
    db = factory()
    row = db.get(ApiKey, UUID(fresh["key_row_id"]))
    assert row is not None
    row.expires_at = datetime.now(UTC) - timedelta(minutes=5)
    db.commit()
    db.close()
    assert client.get("/api/v1/agent/audits", headers=_agent(fresh["key_id"], fresh["secret"])).status_code == 401


def test_only_admins_can_create_api_users_and_keys(api: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, factory = api
    ids = _seed(factory)
    member_csrf = _login(client, "member@example.com", "longenough-password")
    denied = client.post(
        "/api/v1/users",
        json={"name": "Bot", "is_api_user": True, "client_ids": [str(ids["north"])]},
        headers={"X-CSRF-Token": member_csrf, "Origin": "http://127.0.0.1:3000"},
    )
    assert denied.status_code == 403
    denied_key = client.post(
        "/api/v1/api-keys",
        json={"user_id": str(ids["member"])},
        headers={"X-CSRF-Token": member_csrf, "Origin": "http://127.0.0.1:3000"},
    )
    assert denied_key.status_code == 403
    denied_rotate = client.post(
        f"/api/v1/api-keys/{ids['member']}/rotate",
        headers={"X-CSRF-Token": member_csrf, "Origin": "http://127.0.0.1:3000"},
    )
    assert denied_rotate.status_code == 403

    client.cookies.clear()
    admin_csrf = _login(client, "admin@example.com", "longenough-password")
    normal = client.post(
        "/api/v1/users",
        json={
            "email": "new@example.com",
            "name": "New",
            "password": "longenough-password",
            "is_admin": False,
            "client_ids": [],
        },
        headers={"X-CSRF-Token": admin_csrf, "Origin": "http://127.0.0.1:3000"},
    )
    assert normal.status_code == 201, normal.text
    assert normal.json()["is_api_user"] is False
    assert normal.json()["api_credential"] is None
    created = _create_api_user(client, admin_csrf, ids["north"])
    listed = client.get("/api/v1/users")
    assert listed.status_code == 200
    assert created["secret"] not in listed.text
    keys = client.get("/api/v1/api-keys")
    assert keys.status_code == 200
    assert created["secret"] not in keys.text
    assert created["key_id"] in keys.text
    rotated = client.post(
        f"/api/v1/api-keys/{created['key_row_id']}/rotate",
        headers={"X-CSRF-Token": admin_csrf, "Origin": "http://127.0.0.1:3000"},
    )
    assert rotated.status_code == 200
    new_secret = rotated.json()["secret"]
    assert new_secret != created["secret"]
    assert client.get("/api/v1/agent/audits", headers=_agent(created["key_id"], created["secret"])).status_code == 401
    assert client.get("/api/v1/agent/audits", headers=_agent(created["key_id"], new_secret)).status_code == 200
    assert new_secret not in client.get("/api/v1/api-keys").text


def test_api_user_cannot_open_a_browser_session(api: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, factory = api
    ids = _seed(factory)
    csrf = _login(client, "admin@example.com", "longenough-password")
    created = _create_api_user(client, csrf, ids["north"])
    db = factory()
    user = db.get(User, UUID(created["user_id"]))
    assert user is not None
    user.email = "bot@example.com"
    user.password_hash = hash_password("longenough-password")
    db.commit()
    db.close()
    client.cookies.clear()
    token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "bot@example.com", "password": "longenough-password"},
        headers={"X-CSRF-Token": token, "Origin": "http://127.0.0.1:3000"},
    )
    assert login.status_code == 401
    status = client.get("/api/v1/auth/status")
    assert status.json()["authenticated"] is False


def test_tenant_isolation_and_submit_poll_result(api: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, factory = api
    ids = _seed(factory)
    csrf = _login(client, "admin@example.com", "longenough-password")
    north = _create_api_user(client, csrf, ids["north"])
    south_user = client.post(
        "/api/v1/users",
        json={"name": "South bot", "is_api_user": True, "client_ids": [str(ids["south"])]},
        headers={"X-CSRF-Token": csrf, "Origin": "http://127.0.0.1:3000"},
    )
    assert south_user.status_code == 201, south_user.text
    south = south_user.json()["api_credential"]

    created = client.post(
        "/api/v1/agent/audits",
        json={"urls": ["https://example.com/"]},
        headers=_agent(north["key_id"], north["secret"]),
    )
    assert created.status_code == 202, created.text
    assert north["secret"] not in created.text
    audit_id = created.json()["audits"][0]["id"]
    assert created.json()["audits"][0]["status"] == "pending"

    status = client.get(f"/api/v1/agent/audits/{audit_id}/status", headers=_agent(north["key_id"], north["secret"]))
    assert status.status_code == 200
    assert status.json()["status"] == "pending"

    hidden = client.get(f"/api/v1/agent/audits/{audit_id}", headers=_agent(south["key_id"], south["secret"]))
    assert hidden.status_code == 404
    south_list = client.get("/api/v1/agent/audits", headers=_agent(south["key_id"], south["secret"]))
    assert south_list.status_code == 200
    assert audit_id not in south_list.text

    db = factory()
    audit = db.get(Audit, UUID(audit_id))
    assert audit is not None
    assert audit.client_id == ids["north"]
    assert audit.config["source"] == "agent"
    assert audit.config["api_key_id"] == north["key_id"]
    assert north["secret"] not in str(audit.config)
    audit.status = "completed"
    audit.finished_at = datetime.now(UTC)
    audit.overall_score = 81
    audit.seo_score = 75
    audit.geo_score = 88
    audit.pages_crawled = 1
    db.add(Score(audit_id=audit.id, category="overall", score=81, details={"source": "test"}))
    db.add(
        Issue(
            audit_id=audit.id,
            check_id="T01",
            severity="high",
            title="Title missing",
            description="The title is missing.",
            recommendation="Add a title.",
            affected_urls=["https://example.com/"],
            status="fail",
            quick_win=True,
        )
    )
    db.commit()
    db.close()

    result = client.get(f"/api/v1/agent/audits/{audit_id}", headers=_agent(north["key_id"], north["secret"]))
    assert result.status_code == 200
    body = result.json()
    assert body["overall_score"] == 81
    assert body["issues"][0]["title"] == "Title missing"
    assert body["scores"][0]["category"] == "overall"
    again = client.get(f"/api/v1/agent/audits/{audit_id}", headers=_agent(north["key_id"], north["secret"]))
    assert again.status_code == 200
    assert again.json()["issues"][0]["check_id"] == "T01"


def test_ssrf_targets_are_rejected(
    api: tuple[TestClient, sessionmaker[Session]], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, factory = api
    ids = _seed(factory)
    csrf = _login(client, "admin@example.com", "longenough-password")
    created = _create_api_user(client, csrf, ids["north"])
    headers = _agent(created["key_id"], created["secret"])
    for url in ("http://127.0.0.1/", "http://169.254.169.254/", "http://localhost/admin", "http://[::1]/"):
        response = client.post("/api/v1/agent/audits", json={"urls": [url]}, headers=headers)
        assert response.status_code == 400, url
        assert "Traceback" not in response.text

    monkeypatch.setattr(
        "app.services.audit_service.assert_public_url",
        lambda url: assert_public_url(url, resolver=_private),
    )
    rebound = client.post("/api/v1/agent/audits", json={"urls": ["https://rebind.example/"]}, headers=headers)
    assert rebound.status_code == 400
    db = factory()
    assert db.scalar(select(Audit.id)) is None
    db.close()


def test_rate_limit_is_per_key_and_fails_closed(
    api: tuple[TestClient, sessionmaker[Session]], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, factory = api
    ids = _seed(factory)
    csrf = _login(client, "admin@example.com", "longenough-password")
    created = _create_api_user(client, csrf, ids["north"])
    headers = _agent(created["key_id"], created["secret"])
    monkeypatch.setattr(get_settings(), "agent_requests_per_minute", 2)
    assert client.get("/api/v1/agent/audits", headers=headers).status_code == 200
    assert client.get("/api/v1/agent/audits", headers=headers).status_code == 200
    blocked = client.get("/api/v1/agent/audits", headers=headers)
    assert blocked.status_code == 429
    assert created["secret"] not in blocked.text

    redis_keys = [key.decode() if isinstance(key, bytes) else key for key in rate_limit._client().scan_iter("rl:*")]  # type: ignore[attr-defined]
    assert any(created["key_id"] in key for key in redis_keys)
    assert all(created["secret"] not in key for key in redis_keys)

    rate_limit.set_client(_DownRedis())
    down = client.get("/api/v1/agent/audits", headers=headers)
    assert down.status_code == 503
    assert "Traceback" not in down.text
    assert created["secret"] not in down.text


def test_idempotency_replays_the_same_audits(api: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, factory = api
    ids = _seed(factory)
    csrf = _login(client, "admin@example.com", "longenough-password")
    created = _create_api_user(client, csrf, ids["north"])
    headers = {**_agent(created["key_id"], created["secret"]), "Idempotency-Key": "audit-example-1"}
    first = client.post("/api/v1/agent/audits", json={"urls": ["https://example.com/a"]}, headers=headers)
    second = client.post("/api/v1/agent/audits", json={"urls": ["https://example.com/a"]}, headers=headers)
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json() == second.json()
    conflict = client.post("/api/v1/agent/audits", json={"urls": ["https://example.com/b"]}, headers=headers)
    assert conflict.status_code == 409
    db = factory()
    assert len(db.scalars(select(Audit.id)).all()) == 1
    db.close()


def test_scope_and_cookie_are_not_enough(api: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, factory = api
    ids = _seed(factory)
    csrf = _login(client, "admin@example.com", "longenough-password")
    created = _create_api_user(client, csrf, ids["north"], scopes=["audits:read"])
    denied = client.post(
        "/api/v1/agent/audits",
        json={"urls": ["https://example.com/"]},
        headers=_agent(created["key_id"], created["secret"]),
    )
    assert denied.status_code == 403
    cookie_only = client.get("/api/v1/agent/audits")
    assert cookie_only.status_code == 401
    client.cookies.clear()
    browser = client.get("/api/v1/users", headers=_agent(created["key_id"], created["secret"]))
    assert browser.status_code == 401


def test_agent_post_does_not_use_the_csrf_cookie(api: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, factory = api
    ids = _seed(factory)
    csrf = _login(client, "admin@example.com", "longenough-password")
    created = _create_api_user(client, csrf, ids["north"])
    client.cookies.clear()
    accepted = client.post(
        "/api/v1/agent/audits",
        json={"urls": ["https://example.com/"]},
        headers=_agent(created["key_id"], created["secret"]),
    )
    assert accepted.status_code == 202
    rejected = client.post(
        "/api/v1/agent/audits",
        json={"urls": ["https://example.com/elsewhere"]},
        headers={**_agent(created["key_id"], created["secret"]), "Origin": "https://evil.example"},
    )
    assert rejected.status_code == 403


def test_cli_prints_the_secret_once(
    api: tuple[TestClient, sessionmaker[Session]], capfd: pytest.CaptureFixture[str]
) -> None:
    _client, factory = api
    ids = _seed(factory)
    from app.cli import main

    code = main(["create-api-key", "--name", "Nightly", "--client-id", str(ids["north"])])
    captured = capfd.readouterr()
    assert code == 0
    assert "once" in captured.err
    assert "key_id=vak_" in captured.out
    secret = next(line.removeprefix("secret=") for line in captured.out.splitlines() if line.startswith("secret="))
    assert secret.startswith("vas_")
    db = factory()
    row = db.scalar(select(ApiKey))
    assert row is not None
    assert row.secret_hash != secret
    assert secret not in row.secret_hash
    db.close()
    missing = main(["create-api-key", "--name", "Other", "--client-id", "00000000-0000-0000-0000-000000000000"])
    assert missing == 2
    assert "secret=" not in capfd.readouterr().out


def test_openapi_includes_the_placeholder_curl_example(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "expose_docs", True)
    monkeypatch.setattr(get_settings(), "agency_email", "")
    monkeypatch.setattr(get_settings(), "agency_password", "")
    fresh = create_app()
    with TestClient(fresh, base_url="https://testserver") as client:
        response = client.get("/openapi.json")
    assert response.status_code == 200
    text = response.text
    assert "/api/v1/agent/audits" in text
    assert "VISIOAUDIT_API_KEY" in text
    assert "VISIOAUDIT_API_SECRET" in text
    assert "X-Api-Key" in text


def test_unhandled_agent_errors_hide_the_trace(
    api: tuple[TestClient, sessionmaker[Session]], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, factory = api
    ids = _seed(factory)
    csrf = _login(client, "admin@example.com", "longenough-password")
    created = _create_api_user(client, csrf, ids["north"])

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("vas_should_not_leak")

    monkeypatch.setattr("app.api.routes.agent.submit_batch", _boom)
    response = client.post(
        "/api/v1/agent/audits",
        json={"urls": ["https://example.com/"]},
        headers=_agent(created["key_id"], created["secret"]),
    )
    assert response.status_code == 500
    assert response.json()["detail"] == "Interner Fehler."
    assert "Traceback" not in response.text
    assert "vas_should_not_leak" not in response.text
