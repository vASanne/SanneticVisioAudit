"""Redis sliding window shared by more than one client, and fail-closed behavior."""

from __future__ import annotations

import fakeredis
import redis
from app.core import rate_limit
from app.core.rate_limit import RateLimitUnavailable, allow
from app.main import app
from fastapi.testclient import TestClient


class _DownRedis:
    def eval(self, *_args: object, **_kwargs: object) -> int:
        raise redis.RedisError("unavailable")


def test_login_budget_is_ten_per_minute_and_shared() -> None:
    server = fakeredis.FakeServer()
    first = fakeredis.FakeRedis(server=server, decode_responses=True)
    second = fakeredis.FakeRedis(server=server, decode_responses=True)
    rate_limit.set_client(first)
    for _ in range(10):
        assert allow("login:203.0.113.5", limit=10, window_seconds=60)
    rate_limit.set_client(second)
    assert allow("login:203.0.113.5", limit=10, window_seconds=60) is False
    assert allow("login:203.0.113.6", limit=10, window_seconds=60) is True


def test_audit_start_budget_is_thirty_per_hour() -> None:
    for _ in range(30):
        assert allow("audit:user", limit=30, window_seconds=3600)
    assert allow("audit:user", limit=30, window_seconds=3600) is False


def test_redis_errors_fail_closed() -> None:
    rate_limit.set_client(_DownRedis())
    try:
        allow("login:203.0.113.5", limit=10, window_seconds=60)
    except RateLimitUnavailable:
        return
    raise AssertionError("expected RateLimitUnavailable")


def test_login_is_rejected_when_redis_is_unavailable() -> None:
    with TestClient(app, base_url="https://testserver") as client:
        csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        rate_limit.set_client(_DownRedis())
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "person@example.com", "password": "longenough"},
            headers={"X-CSRF-Token": csrf},
        )
    assert response.status_code == 503
    assert "redis" not in response.text.lower()
