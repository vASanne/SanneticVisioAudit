"""Login, session status, and bootstrap of the agency admin."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthUser, optional_user
from app.api.schemas import AuthStatus, LoginRequest, LoginResponse
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import auth_enabled, hash_password, issue_token, verify_password
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/status", response_model=AuthStatus)
def auth_status(user: AuthUser | None = Depends(optional_user)) -> AuthStatus:
    """Tell the dashboard whether login is required and who is signed in."""

    return AuthStatus(
        auth_required=auth_enabled(),
        authenticated=user is not None,
        user_name=user.name if user else None,
        email=user.email if user else None,
        is_admin=bool(user and user.is_admin),
    )


@router.get("/me", response_model=AuthStatus)
def me(user: AuthUser | None = Depends(optional_user)) -> AuthStatus:
    if auth_enabled() and user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Anmeldung erforderlich.")
    return auth_status(user)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    """Issue a bearer token for an agency user."""

    ensure_agency_admin(db)
    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-Mail oder Passwort ist falsch.")
    token = issue_token(AuthUser(id=user.id, email=user.email, name=user.name, is_admin=user.is_admin))
    return LoginResponse(access_token=token, user_name=user.name, email=user.email, is_admin=user.is_admin)


def ensure_agency_admin(db: Session) -> User | None:
    """Create the configured agency admin once, when env credentials exist."""

    settings = get_settings()
    email = settings.agency_email.strip().lower()
    password = settings.agency_password.strip()
    if not email or not password:
        return None
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        # Keep the bootstrapped agency account usable even if it was demoted.
        if not existing.is_admin:
            existing.is_admin = True
            db.commit()
            db.refresh(existing)
        return existing
    user = User(
        email=email,
        name=settings.agency_name.strip() or "Agentur",
        password_hash=hash_password(password),
        is_admin=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
