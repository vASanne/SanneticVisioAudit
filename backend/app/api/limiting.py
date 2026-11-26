"""Map the shared Redis limiter onto HTTP responses.

Unavailable Redis fails closed with 503. An exhausted window is 429.
"""

from __future__ import annotations

from fastapi import HTTPException, status

from app.core.rate_limit import RateLimitUnavailable, allow


def enforce_limit(key: str, *, limit: int, window_seconds: float, detail: str) -> None:
    try:
        permitted = allow(key, limit=limit, window_seconds=window_seconds)
    except RateLimitUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Begrenzung ist vorübergehend nicht verfügbar.",
        ) from exc
    if not permitted:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": "60"},
        )
