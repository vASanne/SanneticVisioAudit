"""Map persistence objects to API responses."""

from __future__ import annotations

from app.api.schemas import AuditDetail, AuditSummary, IssueRead, PageRead, ScoreRead
from app.models import Audit
from app.scoring.prioritize import issue_impact, sort_key


def to_summary(audit: Audit) -> AuditSummary:
    return AuditSummary(
        id=audit.id,
        client_name=audit.client.name,
        client_id=audit.client_id,
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
    settings = dict(audit.client.settings or {}) if audit.client else {}
    paths = settings.get("important_paths")
    important = [str(item) for item in paths] if isinstance(paths, list) else []
    ranked: list[tuple[tuple[object, ...], IssueRead]] = []
    for issue in audit.issues:
        impact = issue_impact(
            severity=issue.severity,
            status=issue.status,
            affected_urls=list(issue.affected_urls or []),
            start_url=audit.url,
            important_paths=important,
            quick_win=issue.quick_win,
        )
        ranked.append(
            (
                sort_key(
                    impact=impact,
                    severity=issue.severity,
                    status=issue.status,
                    quick_win=issue.quick_win,
                    check_id=issue.check_id,
                ),
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
                    impact_score=impact,
                ),
            )
        )
    ranked.sort(key=lambda item: item[0])
    config = dict(audit.config or {})
    llm = config.get("llm_summary_text")
    notes = config.get("gsc_notes")
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
        issues=[item for _, item in ranked],
        scores=[
            ScoreRead(category=score.category, score=score.score, details=score.details or {})
            for score in audit.scores
        ],
        llm_summary=llm if isinstance(llm, str) else None,
        gsc_notes=[str(item) for item in notes] if isinstance(notes, list) else [],
    )
