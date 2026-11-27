"""Machine API. Callers send a key id and a secret. Browser cookies are not accepted.

Authentication is two headers over TLS, not a signed canonical request. The
deployment already terminates TLS at Caddy, and the callers are automated
agents that need a short contract. Request signing would add a canonical
string, a clock skew window, and a nonce store on top of TLS. The secret is
never logged and is stored only as a peppered HMAC. See the tag description
for a curl example with placeholder credentials.
"""

from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.agent_auth import AgentPrincipal, authorize, charge_creates, note_use
from app.api.mappers import to_detail, to_summary
from app.api.schemas import (
    AgentAuditBatch,
    AgentAuditBatchResult,
    AgentAuditStatus,
    AuditDetail,
    AuditSummary,
)
from app.core.config import get_settings
from app.core.database import get_db
from app.crawler.errors import UnsafeUrlError
from app.models import Audit
from app.services.agent_audits import (
    IdempotencyConflict,
    IdempotencyInProgress,
    begin_idempotency,
    checked_idempotency_key,
    prepare_urls,
    release_claim,
    remember,
    request_hash,
    stored_result,
    submit_batch,
)

OPENAPI_TAG_DESCRIPTION = """
Machine-to-machine SEO and GEO audits for one tenant.

Send these headers on every request. The secret is shown once when an agency
admin creates the key. TLS is required; do not send the secret to an `http://` URL.

* `X-Api-Key`: public key id (`vak_...`)
* `X-Api-Secret`: secret (`vas_...`)

Optional on create: `Idempotency-Key` (8 to 200 characters: letters, digits, `.`, `_`, `:`, `-`).
The same key and the same body return the original audit ids. A different body returns 409.

Placeholder credentials only:

```bash
curl -sS -X POST "https://visioaudit.va/api/v1/agent/audits" \\
  -H "Content-Type: application/json" \\
  -H "X-Api-Key: ${VISIOAUDIT_API_KEY}" \\
  -H "X-Api-Secret: ${VISIOAUDIT_API_SECRET}" \\
  -H "Idempotency-Key: audit-example-1" \\
  -d '{"urls":["https://example.com/"]}'
```

Poll, then read the stored scores and findings:

```bash
curl -sS "https://visioaudit.va/api/v1/agent/audits/AUDIT_ID/status" \\
  -H "X-Api-Key: ${VISIOAUDIT_API_KEY}" \\
  -H "X-Api-Secret: ${VISIOAUDIT_API_SECRET}"
```
"""

logger = structlog.get_logger()
router = APIRouter(prefix="/agent", tags=["agent"])

_LOAD = (
    selectinload(Audit.client),
    selectinload(Audit.pages),
    selectinload(Audit.issues),
    selectinload(Audit.scores),
)


def _create(request: Request, db: Session = Depends(get_db)) -> AgentPrincipal:
    return authorize(request, db, "audits:create")


def _read(request: Request, db: Session = Depends(get_db)) -> AgentPrincipal:
    return authorize(request, db, "audits:read")


@router.post(
    "/audits",
    response_model=AgentAuditBatchResult,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit one or more URLs",
    description=(
        "Queues an audit for each public http(s) URL. Private, loopback, link-local, "
        "and metadata addresses are rejected, including after DNS resolution. "
        "Redirect targets are checked again by the crawler before it connects. "
        "The response lists audit ids. Poll `/status`, then GET the audit for scores and findings. "
        "Results are stored in the same audit tables as the dashboard."
    ),
)
def submit_audits(
    payload: AgentAuditBatch,
    request: Request,
    db: Session = Depends(get_db),
    principal: AgentPrincipal = Depends(_create),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> AgentAuditBatchResult | JSONResponse:
    try:
        token = checked_idempotency_key(idempotency_key)
    except ValueError as exc:
        note_use(db, request, principal, "audits.create", 400)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Idempotency-Key is invalid.") from exc
    try:
        urls = prepare_urls(payload, batch_limit=get_settings().agent_batch_limit)
    except UnsafeUrlError as exc:
        note_use(db, request, principal, "audits.create", 400)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL is not a public http(s) address.",
        ) from exc
    except ValueError as exc:
        note_use(db, request, principal, "audits.create", 422)
        detail = "The batch contains the same URL more than once."
        if str(exc) == "batch limit":
            detail = "Too many URLs in one request."
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail) from exc

    charge_creates(request, db, principal, len(urls))
    try:
        claim = begin_idempotency(
            db,
            principal=principal,
            idempotency_key=token,
            digest=request_hash(payload),
        )
    except IdempotencyInProgress as exc:
        note_use(db, request, principal, "audits.create", 409)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key is already in progress.",
        ) from exc
    except IdempotencyConflict as exc:
        note_use(db, request, principal, "audits.create", 409)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key was already used with a different request body.",
        ) from exc

    cached = stored_result(claim)
    if cached is not None:
        note_use(db, request, principal, "audits.create", 202)
        return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=cached)

    try:
        result = submit_batch(db, principal=principal, payload=payload, urls=urls)
    except UnsafeUrlError as exc:
        release_claim(db, claim)
        note_use(db, request, principal, "audits.create", 400)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL is not a public http(s) address.",
        ) from exc
    except Exception as exc:
        release_claim(db, claim)
        note_use(db, request, principal, "audits.create", 500)
        # The exception text can contain a broker URL. Log the type only.
        logger.warning("agent_submit_failed", error_type=type(exc).__name__)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Interner Fehler.") from exc
    body = result.model_dump(mode="json")
    remember(db, claim, body)
    note_use(db, request, principal, "audits.create", 202)
    return result


@router.get("/audits", response_model=list[AuditSummary], summary="List audits for this key's tenant")
def list_audits(
    request: Request,
    db: Session = Depends(get_db),
    principal: AgentPrincipal = Depends(_read),
    limit: int = Query(default=40, ge=1, le=100),
) -> list[AuditSummary]:
    rows = db.scalars(
        select(Audit)
        .where(Audit.client_id == principal.client_id)
        .options(selectinload(Audit.client))
        .order_by(Audit.created_at.desc())
        .limit(limit)
    ).all()
    note_use(db, request, principal, "audits.list", 200)
    return [to_summary(row) for row in rows]


@router.get(
    "/audits/{audit_id}/status",
    response_model=AgentAuditStatus,
    summary="Poll audit status",
)
def audit_status(
    audit_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    principal: AgentPrincipal = Depends(_read),
) -> AgentAuditStatus:
    audit = _owned(db, request, principal, audit_id, "audits.status")
    note_use(db, request, principal, "audits.status", 200)
    return AgentAuditStatus(
        id=audit.id,
        url=audit.url,
        status=audit.status,  # type: ignore[arg-type]
        created_at=audit.created_at,
        started_at=audit.started_at,
        finished_at=audit.finished_at,
        pages_crawled=audit.pages_crawled,
        overall_score=audit.overall_score,
        seo_score=audit.seo_score,
        geo_score=audit.geo_score,
        error_message=audit.error_message,
    )


@router.get(
    "/audits/{audit_id}",
    response_model=AuditDetail,
    summary="Fetch the stored audit result",
    description=(
        "Scores and findings are included when the run has produced them. The row stays stored for later reads."
    ),
)
def audit_result(
    audit_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    principal: AgentPrincipal = Depends(_read),
) -> AuditDetail:
    audit = _owned(db, request, principal, audit_id, "audits.read")
    note_use(db, request, principal, "audits.read", 200)
    return to_detail(audit)


def _owned(db: Session, request: Request, principal: AgentPrincipal, audit_id: UUID, action: str) -> Audit:
    audit = db.scalar(select(Audit).where(Audit.id == audit_id).options(*_LOAD))
    if audit is None or audit.client_id != principal.client_id:
        note_use(db, request, principal, action, 404)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found.")
    return audit
