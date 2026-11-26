"""FastAPI dependencies for optional and required auth."""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import AuthUser, auth_enabled, parse_token
from app.core.sessions import SESSION_COOKIE
from app.models import Membership, User


def optional_user(
    request: Request,
    db: Session = Depends(get_db),
) -> AuthUser | None:
    """Load the user from the HttpOnly session cookie.

    Authorization headers are ignored. A bearer token in page storage is not a session.
    """

    token = request.cookies.get(SESSION_COOKIE, "").strip()
    if not token:
        return None
    user = parse_token(token)
    if user is None:
        return None
    row = db.get(User, user.id)
    if row is None:
        return None
    return AuthUser(id=row.id, email=row.email, name=row.name, is_admin=row.is_admin)


def require_user(user: AuthUser | None = Depends(optional_user)) -> AuthUser:
    if user is not None:
        return user
    if not auth_enabled():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Anmeldung ist nicht konfiguriert. AUTH_SECRET oder AGENCY_EMAIL setzen.",
        )
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Anmeldung erforderlich.")


def require_login(user: AuthUser | None = Depends(optional_user)) -> AuthUser | None:
    """Require a session when auth is enabled; otherwise allow anonymous access."""

    if auth_enabled() and user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Anmeldung erforderlich.")
    return user


def require_admin(user: AuthUser | None = Depends(optional_user)) -> AuthUser | None:
    """Admin-only when auth is on; open when auth is off (local development)."""

    if auth_enabled():
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Anmeldung erforderlich.")
        if not user.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nur Admins dürfen das.")
    return user


def allowed_client_ids(db: Session, user: AuthUser | None) -> set[UUID] | None:
    """None means unrestricted (auth off or admin)."""

    if user is None:
        return None if not auth_enabled() else set()
    if user.is_admin:
        return None
    rows = db.scalars(
        select(Membership.client_id).where(Membership.user_id == user.id)
    ).all()
    return set(rows)


def assert_client_access(db: Session, user: AuthUser | None, client_id: UUID) -> None:
    allowed = allowed_client_ids(db, user)
    if allowed is None:
        return
    if client_id not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kein Zugriff auf diesen Mandanten.")
