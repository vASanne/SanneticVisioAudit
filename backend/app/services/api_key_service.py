"""Create, rotate, and revoke agent keys. The plaintext secret leaves this module only as a return value."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.api_keys import (
    ApiKeyNotConfigured,
    event_key_id,
    generate_key_id,
    generate_secret,
    is_key_id,
    secret_hash,
)
from app.models import ApiKey, ApiKeyEvent, Client, Membership, User

logger = structlog.get_logger()
_SCOPES = ("audits:create", "audits:read")


class ApiKeyError(ValueError):
    """A key change the caller can show to an admin."""


def create_api_user(
    db: Session,
    *,
    name: str,
    client_id: UUID,
    scopes: list[str],
    expires_at: datetime | None,
    created_by: UUID | None,
    email: str | None = None,
) -> tuple[User, ApiKey, str]:
    """Insert an API user, one tenant membership, and the first key.

    The returned string is the secret. Callers show it once and do not log it.
    """

    client = db.get(Client, client_id)
    if client is None:
        raise ApiKeyError("Mandant nicht gefunden.")
    cleaned = name.strip()
    if not cleaned or len(cleaned) > 200:
        raise ApiKeyError("Name ist ungültig.")
    user = User(
        email=email,
        name=cleaned,
        password_hash=None,
        is_admin=False,
        is_api_user=True,
    )
    db.add(user)
    db.flush()
    db.add(Membership(user_id=user.id, client_id=client.id, role="api"))
    key, secret = _insert_key(
        db,
        user_id=user.id,
        client_id=client.id,
        scopes=scopes,
        expires_at=expires_at,
        created_by=created_by,
    )
    logger.info("api_user_created", key_id=key.key_id, client_id=str(client.id))
    return user, key, secret


def issue_key(
    db: Session,
    *,
    user: User,
    scopes: list[str],
    expires_at: datetime | None,
    created_by: UUID | None,
) -> tuple[ApiKey, str]:
    if not user.is_api_user:
        raise ApiKeyError("Schlüssel gibt es nur für API-Nutzer.")
    client_ids = [item.client_id for item in user.memberships]
    if len(client_ids) != 1:
        raise ApiKeyError("Der API-Nutzer braucht genau einen Mandanten.")
    key, secret = _insert_key(
        db,
        user_id=user.id,
        client_id=client_ids[0],
        scopes=scopes,
        expires_at=expires_at,
        created_by=created_by,
    )
    logger.info("api_key_created", key_id=key.key_id, client_id=str(client_ids[0]))
    return key, secret


def rotate_key(db: Session, key: ApiKey) -> str:
    """Replace the stored hash. The previous secret stops working immediately."""

    if key.revoked_at is not None:
        raise ApiKeyError("Ein widerrufener Schlüssel kann nicht rotiert werden.")
    secret = generate_secret()
    key.secret_hash = secret_hash(secret)
    db.flush()
    logger.info("api_key_rotated", key_id=key.key_id)
    return secret


def revoke_key(db: Session, key: ApiKey) -> None:
    if key.revoked_at is None:
        key.revoked_at = datetime.now(UTC)
        db.flush()
    logger.info("api_key_revoked", key_id=key.key_id)


def record_key_event(
    db: Session,
    *,
    api_key: ApiKey | None,
    presented_key: str,
    action: str,
    method: str,
    path: str,
    status_code: int,
) -> None:
    """Append a usage row. ``presented_key`` is reduced to a public id or a short hash."""

    stored_id = event_key_id(presented_key)
    if stored_id.startswith("vas_"):
        stored_id = "rejected"
    db.add(
        ApiKeyEvent(
            api_key_id=api_key.id if api_key is not None else None,
            key_id=stored_id[:80],
            action=action[:32],
            method=method[:8],
            path=_path_only(path),
            status_code=status_code,
        )
    )


def load_key(db: Session, key_id: str) -> ApiKey | None:
    if not is_key_id(key_id):
        return None
    return db.scalar(select(ApiKey).where(ApiKey.key_id == key_id))


def _insert_key(
    db: Session,
    *,
    user_id: UUID,
    client_id: UUID,
    scopes: list[str],
    expires_at: datetime | None,
    created_by: UUID | None,
) -> tuple[ApiKey, str]:
    cleaned_scopes = _clean_scopes(scopes)
    try:
        secret = generate_secret()
        hashed = secret_hash(secret)
    except ApiKeyNotConfigured:
        raise
    key_id = _unused_key_id(db)
    key = ApiKey(
        key_id=key_id,
        secret_hash=hashed,
        user_id=user_id,
        client_id=client_id,
        scopes=cleaned_scopes,
        expires_at=expires_at,
        created_by_user_id=created_by,
    )
    db.add(key)
    db.flush()
    return key, secret


def _clean_scopes(scopes: list[str]) -> list[str]:
    if not scopes or any(item not in _SCOPES for item in scopes):
        raise ApiKeyError("Unbekannter Scope.")
    return [item for item in _SCOPES if item in scopes]


def _unused_key_id(db: Session) -> str:
    for _ in range(5):
        key_id = generate_key_id()
        if db.scalar(select(ApiKey.id).where(ApiKey.key_id == key_id)) is None:
            return key_id
    raise RuntimeError("could not allocate an API key id")


def _path_only(path: str) -> str:
    cleaned = path.split("?", 1)[0].split("#", 1)[0]
    return cleaned[:200]
