"""Map persistence objects to API responses."""

from __future__ import annotations

from app.api.schemas import AuditDetail, AuditSummary, IssueRead, PageRead, ScoreRead
from app.domain import SEVERITY_RANK, STATUS_RANK
from app.models import Audit


def to_summary(audit: Audit) -> AuditSummary:
    return AuditSummary(
        id=audit.id,
        client_name=audit.client.name,
        url=audit.url,
        status=audit.status,  # type: ignore[arg-type]
        created_at=audit.created_at,
        finished_at=audit.finished_at,
        pages_crawled=audit.pages_crawled,
        overall_score=audit.overall_score,
        seo_score=audit.seo_score,
        geo_score=audit.geo_score,
    )


def to_detail(audit: Audit) -> AuditDetail:
    summary = to_summary(audit)
    issues = sorted(audit.issues, key=_issue_key)
    return AuditDetail(
        **summary.model_dump(),
        started_at=audit.started_at,
        error_message=audit.error_message,
        pages=[
            PageRead(
                id=page.id,
                url=page.url,
                final_url=page.final_url,
                status_code=page.status_code,
                title=page.title,
            )
            for page in audit.pages
        ],
        issues=[
            IssueRead(
                id=issue.id,
                check_id=issue.check_id,
                severity=issue.severity,  # type: ignore[arg-type]
                title=issue.title,
                description=issue.description,
                recommendation=issue.recommendation,
                affected_urls=list(issue.affected_urls or []),
                status=issue.status,  # type: ignore[arg-type]
                quick_win=issue.quick_win,
            )
            for issue in issues
        ],
        scores=[
            ScoreRead(category=score.category, score=score.score, details=score.details or {})
            for score in audit.scores
        ],
    )


def _issue_key(issue: object) -> tuple[int, int, int, str]:
    severity = getattr(issue, "severity", "")
    status = getattr(issue, "status", "")
    return (
        SEVERITY_RANK.get(severity, 9),
        STATUS_RANK.get(status, 9),
        0 if getattr(issue, "quick_win", False) else 1,
        str(getattr(issue, "check_id", "")),
    )
