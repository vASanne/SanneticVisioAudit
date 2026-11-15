"""Audit collection and report endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.mappers import to_detail, to_summary
from app.api.schemas import AuditCreate, AuditDetail, AuditSummary
from app.core.database import get_db
from app.crawler.errors import UnsafeUrlError
from app.models import Audit
from app.reports.html import render_audit_report
from app.services.audit_service import QueueUnavailableError, create_audit

router = APIRouter(prefix="/audits", tags=["audits"])

_LOAD = (
    selectinload(Audit.client),
    selectinload(Audit.pages),
    selectinload(Audit.issues),
    selectinload(Audit.scores),
)


@router.post("", response_model=AuditDetail, status_code=status.HTTP_202_ACCEPTED)
def start_audit(payload: AuditCreate, db: Session = Depends(get_db)) -> AuditDetail:
    """Queue a crawl. The response is the audit before any page has been fetched."""

    try:
        audit = create_audit(db, payload)
    except UnsafeUrlError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except QueueUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Die Warteschlange ist nicht erreichbar.",
        ) from exc
    return to_detail(audit)


@router.get("", response_model=list[AuditSummary])
def list_audits(db: Session = Depends(get_db)) -> list[AuditSummary]:
    """Return the most recent audits."""

    rows = db.scalars(
        select(Audit).options(selectinload(Audit.client)).order_by(Audit.created_at.desc()).limit(20)
    ).all()
    return [to_summary(row) for row in rows]


@router.get("/{audit_id}", response_model=AuditDetail)
def get_audit(audit_id: UUID, db: Session = Depends(get_db)) -> AuditDetail:
    """Return one audit, including issues and scores when the run has finished."""

    return to_detail(_get_audit(db, audit_id))


@router.get("/{audit_id}/report", response_class=HTMLResponse)
def get_report(audit_id: UUID, db: Session = Depends(get_db)) -> HTMLResponse:
    """Return the customer HTML report for a completed audit."""

    audit = _get_audit(db, audit_id)
    if audit.status != "completed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Der Bericht ist erst nach Abschluss verfügbar.")
    overall = next((score.details for score in audit.scores if score.category == "overall"), None)
    html = render_audit_report(
        client_name=audit.client.name,
        url=audit.url,
        finished_at=audit.finished_at,
        pages_crawled=audit.pages_crawled,
        scores={
            "overall": audit.overall_score,
            "seo": audit.seo_score,
            "geo": audit.geo_score,
            "technical": _category_score(audit, "technical"),
            "onpage": _category_score(audit, "onpage"),
        },
        overall_details=overall if isinstance(overall, dict) else None,
        issues=to_detail(audit).issues,
        pages=audit.pages,
    )
    return HTMLResponse(html)


def _get_audit(db: Session, audit_id: UUID) -> Audit:
    audit = db.scalar(select(Audit).where(Audit.id == audit_id).options(*_LOAD))
    if audit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit nicht gefunden.")
    return audit


def _category_score(audit: Audit, category: str) -> float | None:
    for score in audit.scores:
        if score.category == category:
            return score.score
    return None
