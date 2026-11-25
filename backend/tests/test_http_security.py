"""Headers, hidden docs, validation errors, and the login rate limit."""

from fastapi.testclient import TestClient

from app.core.rate_limit import allow, reset
from app.main import app


def test_health_sends_security_headers_and_hides_docs() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert response.headers["x-frame-options"] == "DENY"
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
        assert "max-age=31536000" in response.headers["strict-transport-security"]
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404


def test_validation_error_does_not_echo_the_password() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "person@example.com", "password": "hunter2"},
        )
    assert response.status_code == 422
    assert "hunter2" not in response.text
    assert '"input"' not in response.text


def test_login_is_rate_limited() -> None:
    reset()
    for _ in range(10):
        assert allow("login:testclient", limit=10, window_seconds=60)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "person@example.com", "password": "longenough"},
        )
    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"


def test_cross_site_write_is_rejected() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "person@example.com", "password": "longenough"},
            headers={"Origin": "https://evil.example"},
        )
    assert response.status_code == 403
