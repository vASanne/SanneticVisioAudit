"""Client CRUD for white-label settings and tenancy."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthUser, allowed_client_ids, assert_client_access, require_admin, require_login
from app.api.schemas import ClientCreate, ClientRead, ClientUpdate
from app.core.client_settings import SettingsRejected, public_client_settings, sanitize_client_settings
from app.core.database import get_db
from app.core.security import auth_enabled
from app.crawler.errors import UnsafeUrlError
from app.crawler.safety import assert_public_url, logo_reference_is_safe
from app.models import Audit, Client

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientRead])
def list_clients(
    db: Session = Depends(get_db),
    user: AuthUser | None = Depends(require_login),
) -> list[ClientRead]:
    query = select(Client).order_by(Client.name)
    allowed = allowed_client_ids(db, user)
    if allowed is not None:
        if not allowed:
            return []
        query = query.where(Client.id.in_(allowed))
    return [_read(row) for row in db.scalars(query).all()]


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreate,
    db: Session = Depends(get_db),
    _: AuthUser | None = Depends(require_admin),
) -> ClientRead:
    try:
        client = Client(
            name=payload.name.strip(),
            domain=_domain(payload.domain),
            logo_url=_logo(payload.logo_url),
            settings=sanitize_client_settings(payload.settings, existing=None, is_admin=True),
        )
    except (SettingsRejected, UnsafeUrlError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.add(client)
    db.commit()
    db.refresh(client)
    return _read(client)


@router.get("/{client_id}", response_model=ClientRead)
def get_client(
    client_id: UUID,
    db: Session = Depends(get_db),
    user: AuthUser | None = Depends(require_login),
) -> ClientRead:
    client = _get(db, client_id)
    assert_client_access(db, user, client.id)
    return _read(client)


@router.patch("/{client_id}", response_model=ClientRead)
def update_client(
    client_id: UUID,
    payload: ClientUpdate,
    db: Session = Depends(get_db),
    user: AuthUser | None = Depends(require_login),
) -> ClientRead:
    client = _get(db, client_id)
    assert_client_access(db, user, client.id)
    try:
        if payload.name is not None:
            client.name = payload.name.strip()
        if payload.domain is not None:
            client.domain = _domain(payload.domain)
        if payload.logo_url is not None:
            client.logo_url = _logo(payload.logo_url)
        if payload.settings is not None:
            client.settings = sanitize_client_settings(
                payload.settings,
                existing=dict(client.settings or {}),
                is_admin=_is_admin(user),
            )
    except (SettingsRejected, UnsafeUrlError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    db.refresh(client)
    return _read(client)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser | None = Depends(require_admin),
) -> None:
    client = _get(db, client_id)
    # Audits FK to clients without ON DELETE CASCADE, so remove them first.
    for audit in db.scalars(select(Audit).where(Audit.client_id == client.id)).all():
        db.delete(audit)
    db.delete(client)
    db.commit()


def _get(db: Session, client_id: UUID) -> Client:
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mandant nicht gefunden.")
    return client


def _read(client: Client) -> ClientRead:
    return ClientRead(
        id=client.id,
        name=client.name,
        domain=client.domain,
        logo_url=client.logo_url,
        settings=public_client_settings(dict(client.settings or {})),
        created_at=client.created_at,
    )


def _is_admin(user: AuthUser | None) -> bool:
    if not auth_enabled():
        return True
    return bool(user and user.is_admin)


def _domain(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip().lower()
    if not text:
        return None
    if "://" in text or "/" in text or " " in text or "@" in text or len(text) > 255:
        raise SettingsRejected("Die Domain muss ein Hostname sein.")
    return text


def _logo(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    if len(text) > 2000 or not logo_reference_is_safe(text):
        raise SettingsRejected("Die Logo-URL ist nicht erlaubt.")
    assert_public_url(text)
    return text
