"""Agency user administration."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import AuthUser, require_admin
from app.api.schemas import UserCreate, UserRead, UserUpdate
from app.core.database import get_db
from app.core.security import hash_password
from app.models import Client, Membership, User

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db),
    _: AuthUser | None = Depends(require_admin),
) -> list[UserRead]:
    rows = db.scalars(select(User).options(selectinload(User.memberships)).order_by(User.email)).all()
    return [_read(row) for row in rows]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: AuthUser | None = Depends(require_admin),
) -> UserRead:
    email = payload.email.strip().lower()
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Diese E-Mail ist bereits vergeben.")
    user = User(
        email=email,
        name=payload.name.strip(),
        password_hash=hash_password(payload.password),
        is_admin=payload.is_admin,
    )
    db.add(user)
    db.flush()
    _set_memberships(db, user, payload.client_ids)
    db.commit()
    db.refresh(user)
    user = db.scalar(select(User).where(User.id == user.id).options(selectinload(User.memberships)))  # type: ignore[assignment]
    return _read(user)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    actor: AuthUser | None = Depends(require_admin),
) -> UserRead:
    user = db.scalar(select(User).where(User.id == user_id).options(selectinload(User.memberships)))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nutzer nicht gefunden.")
    if payload.email is not None:
        email = payload.email.strip().lower()
        clash = db.scalar(select(User.id).where(User.email == email, User.id != user.id))
        if clash is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Diese E-Mail ist bereits vergeben.")
        user.email = email
    if payload.name is not None:
        user.name = payload.name.strip()
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    if payload.is_admin is not None:
        if actor is not None and actor.id == user.id and payload.is_admin is False:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Eigenen Admin-Status nicht entfernen.")
        user.is_admin = payload.is_admin
    if payload.client_ids is not None:
        _set_memberships(db, user, payload.client_ids)
    db.commit()
    db.refresh(user)
    user = db.scalar(select(User).where(User.id == user.id).options(selectinload(User.memberships)))  # type: ignore[assignment]
    return _read(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    actor: AuthUser | None = Depends(require_admin),
) -> None:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nutzer nicht gefunden.")
    if actor is not None and actor.id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Eigenes Konto kann nicht gelöscht werden.")
    db.delete(user)
    db.commit()


def _set_memberships(db: Session, user: User, client_ids: list[UUID]) -> None:
    wanted = set(client_ids)
    for client_id in wanted:
        if db.get(Client, client_id) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unbekannter Mandant in der Zuordnung.")
    existing = {item.client_id: item for item in user.memberships}
    for client_id, membership in list(existing.items()):
        if client_id not in wanted:
            db.delete(membership)
    for client_id in wanted:
        if client_id not in existing:
            db.add(Membership(user_id=user.id, client_id=client_id, role="member"))


def _read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        email=user.email,
        name=user.name,
        is_admin=user.is_admin,
        client_ids=[item.client_id for item in user.memberships],
        created_at=user.created_at,
    )
