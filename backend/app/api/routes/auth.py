"""Login, session cookie, CSRF token, and bootstrap of the agency admin."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthUser, optional_user
from app.api.limiting import enforce_limit
from app.api.schemas import AuthStatus, CsrfToken, LoginRequest, LoginResponse
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    AuthNotConfigured,
    auth_enabled,
    hash_password,
    issue_token,
    needs_rehash,
    verify_password,
)
from app.core.sessions import (
    SESSION_TTL_SECONDS,
    clear_session_cookie,
    ensure_csrf_cookie,
    rotate_csrf_cookie,
    set_session_cookie,
)
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/csrf", response_model=CsrfToken)
def csrf_token(request: Request, response: Response) -> CsrfToken:
    """Issue the double-submit token. The raw session secret is never included."""

    return CsrfToken(csrf_token=ensure_csrf_cookie(request, response))


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
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> LoginResponse:
    """Check the password and set an HttpOnly session cookie."""

    peer = request.client.host if request.client else "unknown"
    enforce_limit(
        f"login:{peer}",
        limit=10,
        window_seconds=60,
        detail="Zu viele Anmeldeversuche. Bitte kurz warten.",
    )
    ensure_agency_admin(db)
    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    # API users have no password. The dummy check keeps the failure path from
    # returning faster than a real password check.
    stored = ""
    if user is not None and user.password_hash and not user.is_api_user:
        stored = user.password_hash
    password_ok = verify_password(payload.password, stored) and user is not None and not user.is_api_user
    if user is None or not password_ok or not user.email or not user.password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-Mail oder Passwort ist falsch.")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
        db.commit()
        db.refresh(user)
    try:
        token = issue_token(
            AuthUser(id=user.id, email=user.email, name=user.name, is_admin=user.is_admin),
            ttl_seconds=SESSION_TTL_SECONDS,
        )
    except AuthNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Anmeldung ist nicht konfiguriert.",
        ) from exc
    set_session_cookie(response, token)
    csrf = rotate_csrf_cookie(response)
    return LoginResponse(user_name=user.name, email=user.email, is_admin=user.is_admin, csrf_token=csrf)


@router.post("/logout", response_model=CsrfToken)
def logout(response: Response) -> CsrfToken:
    """Clear the session cookie and rotate the CSRF token."""

    clear_session_cookie(response)
    return CsrfToken(csrf_token=rotate_csrf_cookie(response))


def ensure_agency_admin(db: Session) -> User | None:
    """Create the configured agency admin once, when env credentials exist."""

    settings = get_settings()
    email = settings.agency_email.strip().lower()
    password = settings.agency_password.strip()
    if not email or not password:
        return None
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
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
