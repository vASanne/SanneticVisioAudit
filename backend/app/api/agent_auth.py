"""Authenticate an agent request from X-Api-Key and X-Api-Secret.

The session cookie is ignored. A missing pepper or a silent Redis failure
rejects the call. The secret is never written to the usage log.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.limiting import enforce_limit
from app.core.api_keys import ApiKeyNotConfigured, is_key_id, pepper_bytes, rate_identity, secret_matches
from app.core.config import get_settings
from app.models import ApiKey, User
from app.services.api_key_service import load_key, record_key_event

_INVALID = "Invalid API key or secret."
_UNAVAILABLE = "The rate limit store is unavailable."
_PEPPER = "API key verification is not configured."


@dataclass(frozen=True)
class AgentPrincipal:
    key_row_id: UUID
    key_id: str
    user_id: UUID
    client_id: UUID
    scopes: frozenset[str]


def authorize(request: Request, db: Session, scope: str) -> AgentPrincipal:
    try:
        pepper_bytes()
    except ApiKeyNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_PEPPER) from exc

    presented_key = request.headers.get("x-api-key", "").strip()
    presented_secret = request.headers.get("x-api-secret", "")
    identity = rate_identity(presented_key)
    peer = request.client.host if request.client else "unknown"
    if identity == "missing":
        identity = f"anon:{peer}"
    settings = get_settings()
    try:
        enforce_limit(
            f"agent:{identity}",
            limit=settings.agent_requests_per_minute,
            window_seconds=60,
            detail="Too many requests for this API key.",
            unavailable_detail=_UNAVAILABLE,
        )
    except HTTPException as exc:
        _event(db, request, presented_key, None, "rate_limited", exc.status_code)
        raise

    key = load_key(db, presented_key) if is_key_id(presented_key) else None
    user = _user(db, key)
    secret_ok = secret_matches(presented_secret, key.secret_hash if key is not None else "")
    if key is None or user is None or not user.is_api_user or not secret_ok or _inactive(key):
        _event(db, request, presented_key, key if secret_ok else None, "auth_failure", 401)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID)

    key.last_used_at = datetime.now(timezone.utc)
    scopes = frozenset(item for item in (key.scopes or []) if isinstance(item, str))
    if scope not in scopes:
        _event(db, request, presented_key, key, "scope_denied", 403)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This key does not include the required scope.",
        )
    db.commit()
    return AgentPrincipal(
        key_row_id=key.id,
        key_id=key.key_id,
        user_id=user.id,
        client_id=key.client_id,
        scopes=scopes,
    )


def charge_creates(request: Request, db: Session, principal: AgentPrincipal, count: int) -> None:
    settings = get_settings()
    try:
        for _ in range(count):
            enforce_limit(
                f"agent-create:{principal.key_id}",
                limit=settings.agent_creates_per_hour,
                window_seconds=3600,
                detail="Too many audits for this API key. Try again later.",
                unavailable_detail=_UNAVAILABLE,
            )
    except HTTPException as exc:
        _event(db, request, principal.key_id, _reload(db, principal), "rate_limited", exc.status_code)
        raise


def note_use(db: Session, request: Request, principal: AgentPrincipal, action: str, status_code: int) -> None:
    _event(db, request, principal.key_id, _reload(db, principal), action, status_code)


def _inactive(key: ApiKey) -> bool:
    if key.revoked_at is not None:
        return True
    expires = key.expires_at
    if expires is None:
        return False
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires <= datetime.now(timezone.utc)


def _user(db: Session, key: ApiKey | None) -> User | None:
    if key is None:
        return None
    return db.get(User, key.user_id)


def _reload(db: Session, principal: AgentPrincipal) -> ApiKey | None:
    return db.scalar(select(ApiKey).where(ApiKey.id == principal.key_row_id).options(selectinload(ApiKey.user)))


def _event(
    db: Session,
    request: Request,
    presented_key: str,
    key: ApiKey | None,
    action: str,
    status_code: int,
) -> None:
    record_key_event(
        db,
        api_key=key,
        presented_key=presented_key,
        action=action,
        method=request.method,
        path=request.url.path,
        status_code=status_code,
    )
    db.commit()
