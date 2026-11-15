"""Create an audit and hand it to the worker."""

from __future__ import annotations

from urllib.parse import urlsplit

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import AuditCreate
from app.crawler.errors import UnsafeUrlError
from app.crawler.safety import assert_public_url
from app.crawler.urls import normalize_start_url
from app.models import Audit, Client
from app.tasks.audit import run_audit_task

logger = structlog.get_logger()


class QueueUnavailableError(RuntimeError):
    """Redis or the worker broker could not accept the audit."""


def create_audit(db: Session, payload: AuditCreate) -> Audit:
    """Persist a pending audit and enqueue it. The URL is checked before anything is stored."""

    normalized = normalize_start_url(payload.url)
    assert_public_url(normalized)
    name = payload.client_name.strip() or "Intern"
    client = db.scalar(select(Client).where(Client.name == name))
    if client is None:
        client = Client(name=name, domain=urlsplit(normalized).hostname, settings={})
        db.add(client)
        db.flush()
    audit = Audit(
        client=client,
        url=normalized,
        status="pending",
        config={"max_pages": payload.max_pages, "follow_links": payload.follow_links},
    )
    db.add(audit)
    db.commit()
    try:
        run_audit_task.delay(str(audit.id))
    except Exception as exc:
        logger.exception("enqueue_failed", audit_id=str(audit.id))
        audit.status = "failed"
        audit.error_message = "Die Warteschlange ist nicht erreichbar."
        db.commit()
        raise QueueUnavailableError from exc
    return audit


__all__ = ["QueueUnavailableError", "UnsafeUrlError", "create_audit"]
