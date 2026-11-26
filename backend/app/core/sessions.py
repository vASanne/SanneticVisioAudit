"""HttpOnly session cookie and double-submit CSRF token.

The session JWT stays in an HttpOnly cookie so page scripts cannot read it.
The CSRF token is a second cookie plus the same value in a JSON body. The
dashboard and the API are different origins, so the page cannot read the API
cookie. The token is therefore returned only to origins allowed by CORS, and
state-changing requests must echo it in ``X-CSRF-Token``. The cookie itself is
HttpOnly as well.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from typing import Literal

from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings

SESSION_COOKIE = "visioaudit_session"
CSRF_COOKIE = "visioaudit_csrf"
CSRF_HEADER = "x-csrf-token"
SESSION_TTL_SECONDS = 60 * 60 * 12
_CSRF_RE = re.compile(r"^[A-Za-z0-9_-]{32,128}$")
_SameSite = Literal["lax", "strict"]


def issue_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def csrf_cookie_is_trusted(value: str) -> bool:
    return bool(_CSRF_RE.fullmatch(value))


def csrf_tokens_match(cookie: str, header: str) -> bool:
    """Constant-time compare of the CSRF cookie and the request header."""

    if not csrf_cookie_is_trusted(cookie) or not csrf_cookie_is_trusted(header):
        return False
    return hmac.compare_digest(
        hashlib.sha256(cookie.encode("utf-8")).digest(),
        hashlib.sha256(header.encode("utf-8")).digest(),
    )


def ensure_csrf_cookie(request: Request, response: Response) -> str:
    """Return the current CSRF token, or create one.

    A value taken from the request is never written back into ``Set-Cookie``.
    Only ``issue_csrf_token`` chooses a cookie value, so the client cannot
    pick it. A well-formed cookie already stored by the browser is reused for
    the JSON body only.
    """

    existing = request.cookies.get(CSRF_COOKIE, "")
    if csrf_cookie_is_trusted(existing):
        return existing
    return rotate_csrf_cookie(response)


def rotate_csrf_cookie(response: Response) -> str:
    token = issue_csrf_token()
    _set_csrf_cookie(response, token)
    return token


def set_session_cookie(response: Response, token: str) -> None:
    secure, samesite = _cookie_flags()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_TTL_SECONDS,
        path="/",
        secure=secure,
        httponly=True,
        samesite=samesite,
    )


def clear_session_cookie(response: Response) -> None:
    secure, samesite = _cookie_flags()
    response.delete_cookie(
        SESSION_COOKIE,
        path="/",
        secure=secure,
        httponly=True,
        samesite=samesite,
    )


def _set_csrf_cookie(response: Response, token: str) -> None:
    secure, samesite = _cookie_flags()
    response.set_cookie(
        CSRF_COOKIE,
        token,
        max_age=SESSION_TTL_SECONDS,
        path="/",
        secure=secure,
        httponly=True,
        samesite=samesite,
    )


def _cookie_flags() -> tuple[bool, _SameSite]:
    settings = get_settings()
    samesite: _SameSite = "strict" if settings.cookie_samesite == "strict" else "lax"
    return bool(settings.cookie_secure), samesite
