"""Headers, hidden docs, validation errors, and the login rate limit."""

from fastapi.testclient import TestClient

from app.core.http_security import checked_origins, content_security_policy
from app.core.rate_limit import allow, reset
from app.main import app
from app.reports.html import render_audit_report, report_style_hash


def test_health_sends_security_headers_and_hides_docs() -> None:
    with TestClient(app, base_url="https://testserver") as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert response.headers["x-frame-options"] == "DENY"
        policy = response.headers["content-security-policy"]
        assert "frame-ancestors 'none'" in policy
        assert "unsafe-inline" not in policy
        assert "max-age=31536000" in response.headers["strict-transport-security"]
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404


def test_validation_error_does_not_echo_the_password() -> None:
    with TestClient(app, base_url="https://testserver") as client:
        csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "person@example.com", "password": "hunter2"},
            headers={"X-CSRF-Token": csrf},
        )
    assert response.status_code == 422
    assert "hunter2" not in response.text
    assert '"input"' not in response.text


def test_login_is_rate_limited() -> None:
    reset()
    for _ in range(10):
        assert allow("login:testclient", limit=10, window_seconds=60)
    with TestClient(app, base_url="https://testserver") as client:
        csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "person@example.com", "password": "longenough"},
            headers={"X-CSRF-Token": csrf},
        )
    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"


def test_cross_site_write_is_rejected() -> None:
    with TestClient(app, base_url="https://testserver") as client:
        csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "person@example.com", "password": "longenough"},
            headers={"Origin": "https://evil.example", "X-CSRF-Token": csrf},
        )
    assert response.status_code == 403
    assert response.json()["detail"] == "Origin nicht erlaubt."


def test_wildcard_origin_is_rejected() -> None:
    try:
        checked_origins(["https://audit.example", "*"])
    except RuntimeError as exc:
        assert "*" in str(exc)
        return
    raise AssertionError("wildcard origin was accepted")


def test_html_response_csp_uses_the_style_hash() -> None:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse

    from app.core.http_security import STYLE_HASH_HEADER, SecurityMiddleware

    document = "<html><style>body{color:#111}</style></html>"
    digest = report_style_hash(document)
    mini = FastAPI()

    @mini.get("/report")
    def report() -> HTMLResponse:
        return HTMLResponse(document, headers={STYLE_HASH_HEADER: digest})

    mini.add_middleware(SecurityMiddleware, allowed_origins=["http://127.0.0.1:3000"])
    response = TestClient(mini).get("/report")
    policy = response.headers["content-security-policy"]
    assert response.status_code == 200
    assert "unsafe-inline" not in policy
    assert f"'sha256-{digest}'" in policy
    assert "x-report-style-hash" not in response.headers


def test_report_csp_hashes_styles_and_drops_unsafe_inline() -> None:
    html = render_audit_report(
        client_name="Kunde",
        url="https://example.com/",
        finished_at=None,
        pages_crawled=0,
        scores={"overall": None, "seo": None, "geo": None, "technical": None, "onpage": None},
        overall_details={"checks": []},
        issues=[],
        pages=[],
    )
    assert html.count("<style>") == 1
    assert "style=" not in html
    digest = report_style_hash(html)
    policy = content_security_policy(media_type="text/html; charset=utf-8", style_hash=digest)
    assert "unsafe-inline" not in policy
    assert f"style-src 'sha256-{digest}'" in policy
    assert "script-src 'none'" in policy
