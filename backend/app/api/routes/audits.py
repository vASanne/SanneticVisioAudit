"""Audit collection and report endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import AuthUser, allowed_client_ids, assert_client_access, require_login
from app.api.limiting import enforce_limit
from app.api.mappers import to_detail, to_summary
from app.api.schemas import AuditCreate, AuditDetail, AuditSummary
from app.core.database import get_db
from app.core.http_security import STYLE_HASH_HEADER
from app.crawler.errors import UnsafeUrlError
from app.crawler.render import RenderUnavailableError
from app.models import Audit
from app.reports.html import render_audit_report, report_branding, report_style_hash
from app.reports.pdf import render_audit_pdf
from app.services.audit_service import QueueUnavailableError, create_audit

router = APIRouter(prefix="/audits", tags=["audits"])

_LOAD = (
    selectinload(Audit.client),
    selectinload(Audit.pages),
    selectinload(Audit.issues),
    selectinload(Audit.scores),
)


@router.post("", response_model=AuditDetail, status_code=status.HTTP_202_ACCEPTED)
def start_audit(
    payload: AuditCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: AuthUser | None = Depends(require_login),
) -> AuditDetail:
    """Queue a crawl. The response is the audit before any page has been fetched."""

    peer = str(user.id) if user is not None else (request.client.host if request.client else "unknown")
    enforce_limit(
        f"audit:{peer}",
        limit=30,
        window_seconds=3600,
        detail="Zu viele Audits in kurzer Zeit. Bitte später erneut versuchen.",
    )
    try:
        audit = create_audit(db, payload, user=user)
    except UnsafeUrlError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except QueueUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Die Warteschlange ist nicht erreichbar.",
        ) from exc
    return to_detail(audit)


@router.get("", response_model=list[AuditSummary])
def list_audits(
    db: Session = Depends(get_db),
    user: AuthUser | None = Depends(require_login),
) -> list[AuditSummary]:
    """Return the most recent audits."""

    query = select(Audit).options(selectinload(Audit.client)).order_by(Audit.created_at.desc()).limit(40)
    allowed = allowed_client_ids(db, user)
    if allowed is not None:
        if not allowed:
            return []
        query = query.where(Audit.client_id.in_(allowed))
    rows = db.scalars(query).all()
    return [to_summary(row) for row in rows]


@router.get("/{audit_id}", response_model=AuditDetail)
def get_audit(
    audit_id: UUID,
    db: Session = Depends(get_db),
    user: AuthUser | None = Depends(require_login),
) -> AuditDetail:
    """Return one audit, including issues and scores when the run has finished."""

    return to_detail(_get_audit(db, audit_id, user))


@router.get("/{audit_id}/report", response_class=HTMLResponse)
def get_report(
    audit_id: UUID,
    db: Session = Depends(get_db),
    user: AuthUser | None = Depends(require_login),
) -> HTMLResponse:
    """Return the customer HTML report for a completed audit."""

    document = _render_html(_get_audit(db, audit_id, user))
    return HTMLResponse(document, headers={STYLE_HASH_HEADER: report_style_hash(document)})


@router.get("/{audit_id}/report.pdf")
def get_report_pdf(
    audit_id: UUID,
    db: Session = Depends(get_db),
    user: AuthUser | None = Depends(require_login),
) -> Response:
    """Return the customer PDF report for a completed audit."""

    audit = _get_audit(db, audit_id, user)
    html = _render_html(audit)
    try:
        pdf = render_audit_pdf(html)
    except RenderUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="audit-{audit_id}.pdf"'},
    )


def _render_html(audit: Audit) -> str:
    if audit.status != "completed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Der Bericht ist erst nach Abschluss verfügbar.")
    overall = next((score.details for score in audit.scores if score.category == "overall"), None)
    brand = report_branding(audit.client.settings if audit.client else {}, audit.client.logo_url if audit.client else None)
    detail = to_detail(audit)
    return render_audit_report(
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
        issues=detail.issues,
        pages=audit.pages,
        logo_url=brand["logo_url"],
        white_label=bool(brand["white_label"]),
        theme_tokens=brand["theme_tokens"],
        llm_summary=detail.llm_summary,
        gsc_notes=detail.gsc_notes,
    )


def _get_audit(db: Session, audit_id: UUID, user: AuthUser | None) -> Audit:
    audit = db.scalar(select(Audit).where(Audit.id == audit_id).options(*_LOAD))
    if audit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit nicht gefunden.")
    assert_client_access(db, user, audit.client_id)
    return audit


def _category_score(audit: Audit, category: str) -> float | None:
    for score in audit.scores:
        if score.category == category:
            return score.score
    return None


