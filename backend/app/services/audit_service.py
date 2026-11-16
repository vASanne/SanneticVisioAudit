"""Create an audit and hand it to the worker."""

from __future__ import annotations

from urllib.parse import urlsplit
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.schemas import AuditCreate
from app.core.security import AuthUser
from app.crawler.errors import UnsafeUrlError
from app.crawler.safety import assert_public_url
from app.crawler.urls import normalize_start_url
from app.models import Audit, Client, Membership
from app.tasks.audit import run_audit_task

logger = structlog.get_logger()


class QueueUnavailableError(RuntimeError):
    """Redis or the worker broker could not accept the audit."""


def create_audit(db: Session, payload: AuditCreate, user: AuthUser | None = None) -> Audit:
    """Persist a pending audit and enqueue it. The URL is checked before anything is stored."""

    normalized = normalize_start_url(payload.url)
    assert_public_url(normalized)
    client = _resolve_client(db, payload, user, hostname=urlsplit(normalized).hostname)
    audit = Audit(
        client=client,
        url=normalized,
        status="pending",
        config={
            "max_pages": payload.max_pages,
            "follow_links": payload.follow_links,
            "render_js": payload.render_js,
            "probe_internal_links": payload.probe_internal_links,
            "llm_summary": payload.llm_summary,
        },
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    audit = db.scalar(select(Audit).where(Audit.id == audit.id).options(selectinload(Audit.client)))  # type: ignore[assignment]
    try:
        run_audit_task.delay(str(audit.id))
    except Exception as exc:
        logger.exception("enqueue_failed", audit_id=str(audit.id))
        audit.status = "failed"
        audit.error_message = "Die Warteschlange ist nicht erreichbar."
        db.commit()
        raise QueueUnavailableError from exc
    return audit


def _resolve_client(
    db: Session,
    payload: AuditCreate,
    user: AuthUser | None,
    *,
    hostname: str | None,
) -> Client:
    if payload.client_id is not None:
        client = db.get(Client, payload.client_id)
        if client is None:
            raise PermissionError("Mandant nicht gefunden.")
        _assert_access(db, user, client.id)
        return client
    name = payload.client_name.strip() or "Intern"
    client = db.scalar(select(Client).where(Client.name == name))
    if client is None:
        client = Client(name=name, domain=hostname, settings={})
        db.add(client)
        db.flush()
        if user is not None and not user.is_admin:
            db.add(Membership(user_id=user.id, client_id=client.id, role="owner"))
            db.flush()
        return client
    _assert_access(db, user, client.id)
    return client


def _assert_access(db: Session, user: AuthUser | None, client_id: UUID) -> None:
    if user is None or user.is_admin:
        return
    membership = db.scalar(
        select(Membership.id).where(Membership.user_id == user.id, Membership.client_id == client_id)
    )
    if membership is None:
        raise PermissionError("Kein Zugriff auf diesen Mandanten.")


__all__ = ["QueueUnavailableError", "UnsafeUrlError", "create_audit"]
