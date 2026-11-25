"""Synchronous database sessions shared by the API and Celery."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def _engine_url() -> str:
    url = get_settings().database_url.strip()
    # Import-time fallback so unit tests can load the app without a database.
    # Requests that need rows still require DATABASE_URL.
    return url or "sqlite:///:memory:"


def _connect_args(url: str) -> dict[str, object]:
    if url.startswith("postgresql"):
        return {"connect_timeout": 5}
    return {}


_URL = _engine_url()
engine = create_engine(
    _URL,
    pool_pre_ping=_URL.startswith("postgresql"),
    connect_args=_connect_args(_URL),
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency that closes the session after the request."""

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Open a session for a worker task. Callers commit explicitly."""

    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
