"""Agency-admin key management. Responses list metadata only, except the one-time secret."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import AuthUser, require_admin
from app.api.schemas import ApiCredential, ApiKeyCreate, ApiKeyCreated, ApiKeyRead
from app.core.api_keys import ApiKeyNotConfigured
from app.core.database import get_db
from app.models import ApiKey, User
from app.services.api_key_service import ApiKeyError, issue_key, record_key_event, revoke_key, rotate_key

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("", response_model=list[ApiKeyRead])
def list_keys(
    db: Session = Depends(get_db),
    _: AuthUser | None = Depends(require_admin),
) -> list[ApiKeyRead]:
    rows = db.scalars(select(ApiKey).order_by(ApiKey.created_at.desc())).all()
    return [_read(row) for row in rows]


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
def create_key(
    payload: ApiKeyCreate,
    db: Session = Depends(get_db),
    actor: AuthUser | None = Depends(require_admin),
) -> ApiKeyCreated:
    user = db.scalar(select(User).where(User.id == payload.user_id).options(selectinload(User.memberships)))
    if user is None or not user.is_api_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API-Nutzer nicht gefunden.")
    try:
        key, secret = issue_key(
            db,
            user=user,
            scopes=payload.scopes,
            expires_at=payload.expires_at,
            created_by=actor.id if actor is not None else None,
        )
    except ApiKeyNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="API-Schlüssel sind nicht konfiguriert.") from exc
    except ApiKeyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    record_key_event(
        db,
        api_key=key,
        presented_key=key.key_id,
        action="created",
        method="POST",
        path="/api/v1/api-keys",
        status_code=201,
    )
    db.commit()
    db.refresh(key)
    return _created(key, secret)


@router.post("/{key_row_id}/revoke", response_model=ApiKeyRead)
def revoke(
    key_row_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser | None = Depends(require_admin),
) -> ApiKeyRead:
    key = _get(db, key_row_id)
    revoke_key(db, key)
    record_key_event(
        db,
        api_key=key,
        presented_key=key.key_id,
        action="revoked",
        method="POST",
        path="/api/v1/api-keys/revoke",
        status_code=200,
    )
    db.commit()
    db.refresh(key)
    return _read(key)


@router.post("/{key_row_id}/rotate", response_model=ApiCredential)
def rotate(
    key_row_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser | None = Depends(require_admin),
) -> ApiCredential:
    key = _get(db, key_row_id)
    try:
        secret = rotate_key(db, key)
    except ApiKeyNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="API-Schlüssel sind nicht konfiguriert.") from exc
    except ApiKeyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    record_key_event(
        db,
        api_key=key,
        presented_key=key.key_id,
        action="rotated",
        method="POST",
        path="/api/v1/api-keys/rotate",
        status_code=200,
    )
    db.commit()
    return ApiCredential(key_id=key.key_id, secret=secret)


def _get(db: Session, key_row_id: UUID) -> ApiKey:
    key = db.get(ApiKey, key_row_id)
    if key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API-Schlüssel nicht gefunden.")
    return key


def _read(key: ApiKey) -> ApiKeyRead:
    return ApiKeyRead(
        id=key.id,
        key_id=key.key_id,
        client_id=key.client_id,
        scopes=list(key.scopes or []),
        expires_at=key.expires_at,
        revoked_at=key.revoked_at,
        last_used_at=key.last_used_at,
        created_at=key.created_at,
    )


def _created(key: ApiKey, secret: str) -> ApiKeyCreated:
    return ApiKeyCreated(**_read(key).model_dump(), secret=secret)
