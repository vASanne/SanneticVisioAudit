"""Security headers, a strict default CSP, and an Origin check for writes."""

from __future__ import annotations

from collections.abc import Sequence

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}
_API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
_REPORT_CSP = (
    "default-src 'none'; script-src 'none'; style-src 'unsafe-inline'; "
    "img-src data: https:; font-src data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Attach browser hardening headers and reject cross-site writes."""

    def __init__(self, app: object, allowed_origins: Sequence[str]) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._allowed = {origin.rstrip("/") for origin in allowed_origins}

    async def dispatch(self, request: Request, call_next: object) -> Response:
        if request.method in _UNSAFE:
            origin = request.headers.get("origin")
            if origin and origin.rstrip("/") not in self._allowed:
                return JSONResponse(status_code=403, content={"detail": "Origin nicht erlaubt."})
        response = await call_next(request)  # type: ignore[misc]
        path = request.url.path
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Cross-Origin-Resource-Policy"] = "same-site"
        response.headers["Content-Security-Policy"] = _csp_for(response)
        response.headers.setdefault("Cache-Control", "no-store" if path.startswith("/api/") else "no-cache")
        if "server" in response.headers:
            del response.headers["server"]
        return response


def _csp_for(response: Response) -> str:
    media = response.media_type or ""
    if media.startswith("text/html"):
        return _REPORT_CSP
    return _API_CSP


def checked_origins(origins: Sequence[str]) -> list[str]:
    """Reject a wildcard origin. Credentials are never combined with one."""

    cleaned = [item.rstrip("/") for item in origins if item.strip()]
    if "*" in cleaned:
        raise RuntimeError("CORS origin * is not allowed")
    return cleaned
