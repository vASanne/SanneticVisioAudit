"""Liveness is public, minimal, and independent of Redis."""

import redis
from app.core import rate_limit
from app.main import app
from fastapi.testclient import TestClient


class _DownRedis:
    def eval(self, *_args: object, **_kwargs: object) -> int:
        raise redis.RedisError("unavailable")


def test_health() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_public_health_matches_the_container_probe() -> None:
    with TestClient(app) as client:
        inside = client.get("/health")
        public = client.get("/api/v1/health")
    assert inside.status_code == 200
    assert public.status_code == 200
    assert public.json() == {"status": "ok"}
    assert set(public.json()) == {"status"}
    assert public.json() == inside.json()


def test_public_health_needs_no_session_or_csrf_and_ignores_redis() -> None:
    rate_limit.set_client(_DownRedis())
    with TestClient(app) as client:
        for _ in range(15):
            response = client.get("/api/v1/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
    assert "visioaudit_session" not in response.headers.get("set-cookie", "")
