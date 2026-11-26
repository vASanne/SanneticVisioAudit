"""Submit a batch of audits for one agent key and remember Idempotency-Key retries."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.agent_auth import AgentPrincipal
from app.api.schemas import AgentAuditBatch, AgentAuditBatchResult, AuditCreate
from app.crawler.errors import UnsafeUrlError
from app.crawler.safety import assert_public_url
from app.crawler.urls import normalize_start_url
from app.models import ApiIdempotency, ApiKey, Audit
from app.services.audit_service import create_audit
from app.tasks.audit import run_audit_task

_IDEM = re.compile(r"^[A-Za-z0-9._:-]{8,200}$")
_CLAIM_TTL = timedelta(seconds=60)


class IdempotencyConflict(Exception):
    """The same key was already used for a different body, or a request is still running."""


class IdempotencyInProgress(IdempotencyConflict):
    """A matching request has not stored its response yet."""


def checked_idempotency_key(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    if not _IDEM.fullmatch(value):
        raise ValueError("invalid idempotency key")
    return value


def prepare_urls(payload: AgentAuditBatch, *, batch_limit: int) -> list[str]:
    """Normalize and reject non-public URLs before any row is written."""

    if len(payload.urls) > batch_limit:
        raise ValueError("batch limit")
    normalized: list[str] = []
    for raw in payload.urls:
        url = normalize_start_url(raw)
        assert_public_url(url)
        normalized.append(url)
    if len(set(normalized)) != len(normalized):
        raise ValueError("duplicate")
    return normalized


def request_hash(payload: AgentAuditBatch) -> str:
    raw = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def begin_idempotency(
    db: Session,
    *,
    principal: AgentPrincipal,
    idempotency_key: str | None,
    digest: str,
) -> ApiIdempotency | None:
    """Claim the key. A stored body is returned by the caller without creating audits."""

    if idempotency_key is None:
        return None
    existing = _find(db, principal.key_row_id, idempotency_key)
    if existing is not None:
        return _usable(existing, digest)
    row = ApiIdempotency(
        api_key_id=principal.key_row_id,
        idempotency_key=idempotency_key,
        request_hash=digest,
        status_code=0,
        response_body=None,
    )
    try:
        db.add(row)
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = _find(db, principal.key_row_id, idempotency_key)
        if existing is None:
            raise
        return _usable(existing, digest)
    return row


def stored_result(row: ApiIdempotency | None) -> dict[str, Any] | None:
    if row is None or row.response_body is None:
        return None
    body = row.response_body
    if isinstance(body, dict) and "audits" in body:
        return body
    return None


def release_claim(db: Session, row: ApiIdempotency | None) -> None:
    if row is None or row.response_body is not None:
        return
    db.delete(row)
    db.commit()


def remember(db: Session, row: ApiIdempotency | None, body: dict[str, Any]) -> None:
    if row is None:
        return
    row.status_code = 202
    row.response_body = body
    db.commit()


def submit_batch(
    db: Session,
    *,
    principal: AgentPrincipal,
    payload: AgentAuditBatch,
    urls: list[str],
) -> AgentAuditBatchResult:
    key = db.get(ApiKey, principal.key_row_id)
    key_id = key.key_id if key is not None else principal.key_id
    created: list[Audit] = []
    queue_failed = False
    for url in urls:
        audit = create_audit(
            db,
            AuditCreate(
                url=url,
                max_pages=payload.max_pages,
                follow_links=payload.follow_links,
                render_js=payload.render_js,
                probe_internal_links=payload.probe_internal_links,
                llm_summary=payload.llm_summary,
                client_id=principal.client_id,
            ),
            extra_config={"source": "agent", "api_key_id": key_id},
            enqueue=False,
        )
        created.append(audit)
    for audit in created:
        if queue_failed:
            _mark_unqueued(db, audit)
            continue
        try:
            run_audit_task.delay(str(audit.id))
        except Exception:
            # The broker error can include a URL. Keep it out of the log and the client body.
            queue_failed = True
            _mark_unqueued(db, audit)
    return AgentAuditBatchResult(
        audits=[{"id": item.id, "url": item.url, "status": item.status} for item in created]
    )


def _mark_unqueued(db: Session, audit: Audit) -> None:
    audit.status = "failed"
    audit.error_message = "Die Warteschlange ist nicht erreichbar."
    db.commit()


def _find(db: Session, api_key_id: object, idempotency_key: str) -> ApiIdempotency | None:
    return db.scalar(
        select(ApiIdempotency).where(
            ApiIdempotency.api_key_id == api_key_id,
            ApiIdempotency.idempotency_key == idempotency_key,
        )
    )


def _usable(existing: ApiIdempotency, digest: str) -> ApiIdempotency:
    import hmac

    if not hmac.compare_digest(existing.request_hash, digest):
        raise IdempotencyConflict
    if existing.response_body is None and not _stale(existing):
        raise IdempotencyInProgress
    if existing.response_body is None and _stale(existing):
        return existing
    return existing


def _stale(existing: ApiIdempotency) -> bool:
    created = existing.created_at
    if created is None:
        return True
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - created > _CLAIM_TTL
