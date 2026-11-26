"""Liveness probe.

Both paths return the same body. ``/health`` is for the container healthcheck.
``/api/v1/health`` is the public path, because Caddy only forwards ``/api/*``.

The probe is a GET, so the CSRF check does not apply. It does not use the
Redis rate limiter: a Redis outage must not make the probe fail, and probes
must not consume the login window.
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


def _status() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health", operation_id="health_liveness")
def health() -> dict[str, str]:
    """Report that the API process is answering."""

    return _status()


@router.get("/api/v1/health", operation_id="health_liveness_public")
def health_public() -> dict[str, str]:
    """Same liveness probe on the path Caddy forwards."""

    return _status()
