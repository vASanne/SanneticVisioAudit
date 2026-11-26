"""Security headers, a strict default CSP, and checks for cross-site writes.

State-changing browser requests must pass the Origin allow-list and a
double-submit CSRF check. Safe methods are not CSRF-protected.

``/api/v1/agent/`` is the machine API. It does not use the session cookie, so
the CSRF cookie is not a credential there. Callers send ``X-Api-Key`` and
``X-Api-Secret`` instead. Those headers make the request non-simple, so a
cross-site browser form cannot attach them. A disallowed Origin is still
rejected when a browser sends one.
"""

from __future__ import annotations

from collections.abc import Sequence

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.sessions import CSRF_COOKIE, CSRF_HEADER, csrf_tokens_match

_UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}
STYLE_HASH_HEADER = "x-report-style-hash"
_API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"


class SecurityMiddleware(BaseHTTPMiddleware):
    """Attach browser hardening headers and reject cross-site writes."""

    def __init__(self, app: object, allowed_origins: Sequence[str]) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._allowed = {origin.rstrip("/") for origin in allowed_origins}

    async def dispatch(self, request: Request, call_next: object) -> Response:
        if request.method in _UNSAFE:
            rejection = self._reject_write(request)
            if rejection is not None:
                return self._finish(request, rejection)
        response = await call_next(request)  # type: ignore[misc]
        return self._finish(request, response)

    def _reject_write(self, request: Request) -> JSONResponse | None:
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") not in self._allowed:
            return JSONResponse(status_code=403, content={"detail": "Origin nicht erlaubt."})
        if _is_agent_api(request.url.path):
            return None
        cookie = request.cookies.get(CSRF_COOKIE, "")
        header = request.headers.get(CSRF_HEADER, "")
        if not csrf_tokens_match(cookie, header):
            return JSONResponse(status_code=403, content={"detail": "CSRF-Token fehlt oder ist ungültig."})
        return None

    def _finish(self, request: Request, response: Response) -> Response:
        style_hash = response.headers.get(STYLE_HASH_HEADER) or None
        if STYLE_HASH_HEADER in response.headers:
            del response.headers[STYLE_HASH_HEADER]
        path = request.url.path
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Cross-Origin-Resource-Policy"] = "same-site"
        response.headers["Content-Security-Policy"] = content_security_policy(
            media_type=_media_type(response),
            style_hash=style_hash,
        )
        response.headers.setdefault("Cache-Control", "no-store" if path.startswith("/api/") else "no-cache")
        if "server" in response.headers:
            del response.headers["server"]
        return response


def _media_type(response: Response) -> str:
    # BaseHTTPMiddleware can leave media_type empty and keep the header only.
    if response.media_type:
        return response.media_type
    return response.headers.get("content-type", "")


def content_security_policy(*, media_type: str, style_hash: str | None = None) -> str:
    """CSP for API JSON, or for an HTML report whose style block is hashed.

    Style hashes replace ``unsafe-inline``. A missing hash means the document
    has no style block, so styles are denied.
    """

    if media_type.startswith("text/html"):
        style_src = f"'sha256-{style_hash}'" if style_hash else "'none'"
        return (
            "default-src 'none'; script-src 'none'; "
            f"style-src {style_src}; "
            "img-src data: https:; font-src data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
        )
    return _API_CSP


def _is_agent_api(path: str) -> bool:
    return path == "/api/v1/agent" or path.startswith("/api/v1/agent/")


def checked_origins(origins: Sequence[str]) -> list[str]:
    """Reject a wildcard origin. Credentials are never combined with one."""

    cleaned = [item.rstrip("/") for item in origins if item.strip()]
    if "*" in cleaned:
        raise RuntimeError("CORS origin * is not allowed")
    return cleaned
