"""Run one audit from crawl through score."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from uuid import UUID

import structlog
from celery.exceptions import SoftTimeLimitExceeded

from app.analyzers.engine import run_checks
from app.core.config import get_settings
from app.core.database import session_scope
from app.core.logging import setup_logging
from app.crawler.errors import UnsafeUrlError
from app.crawler.runner import CrawlOptions, crawl_site
from app.crawler.types import CrawlOutput
from app.domain import CategoryScore, CheckResult, PageSnapshot, SiteContext
from app.extractors.html_extract import extract_page
from app.models import Audit, Issue, Page, Score
from app.scoring.engine import score_checks
from app.services.storage import ObjectStorage

logger = structlog.get_logger()


def execute_audit(audit_id: UUID) -> None:
    """Claim a pending audit, crawl it, and store checks plus scores."""

    setup_logging()
    log = logger.bind(audit_id=str(audit_id))
    try:
        claimed = _claim(audit_id)
        if claimed is None:
            log.info("audit_skipped")
            return
        start_url, options = claimed
        log.info("audit_started", url=start_url)
        output = _crawl(start_url, options)
        snapshots = tuple(extract_page(page) for page in output.pages)
        context = SiteContext(
            start_url=start_url,
            user_agent=options.user_agent,
            robots_txt=output.robots_txt,
            robots_status=output.robots_status,
            pages=snapshots,
            blocked_by_robots=output.blocked_by_robots,
        )
        checks = run_checks(context)
        scores = score_checks(checks)
        _persist(audit_id, output, snapshots, checks, scores)
        log.info("audit_completed", pages=len(snapshots), checks=len(checks))
    except UnsafeUrlError as exc:
        log.warning("audit_rejected", reason=str(exc))
        _mark_failed(audit_id, str(exc))
    except SoftTimeLimitExceeded:
        log.warning("audit_time_limit")
        _mark_failed(audit_id, "Das Audit hat das Zeitlimit überschritten.")
    except Exception:
        log.exception("audit_failed")
        _mark_failed(audit_id, "Das Audit ist wegen eines internen Fehlers fehlgeschlagen.")


def _crawl(start_url: str, options: CrawlOptions) -> CrawlOutput:
    import asyncio

    return asyncio.run(crawl_site(start_url, options))


def _claim(audit_id: UUID) -> tuple[str, CrawlOptions] | None:
    with session_scope() as db:
        audit = db.get(Audit, audit_id)
        if audit is None or audit.status != "pending":
            return None
        audit.status = "running"
        audit.started_at = datetime.now(timezone.utc)
        options = _options(audit.config or {})
        url = audit.url
        db.commit()
        return url, options


def _options(config: dict[str, object]) -> CrawlOptions:
    settings = get_settings()
    raw_pages = config.get("max_pages", 25)
    try:
        requested = int(raw_pages)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        requested = 25
    follow = config.get("follow_links", True)
    return CrawlOptions(
        user_agent=settings.user_agent,
        max_pages=max(1, min(requested, settings.max_pages_cap)),
        follow_links=follow is not False,
        delay_seconds=max(0.0, settings.crawl_delay_seconds),
    )


def _persist(
    audit_id: UUID,
    output: CrawlOutput,
    snapshots: tuple[PageSnapshot, ...],
    checks: list[CheckResult],
    scores: list[CategoryScore],
) -> None:
    storage = ObjectStorage(get_settings())
    bucket_ready = True
    try:
        storage.ensure_bucket()
    except Exception:
        logger.exception("storage_unavailable", audit_id=str(audit_id))
        bucket_ready = False

    with session_scope() as db:
        audit = db.get(Audit, audit_id)
        if audit is None:
            return
        for position, (crawled, snapshot) in enumerate(zip(output.pages, snapshots, strict=True)):
            page_id = uuid.uuid4()
            storage_path = None
            if bucket_ready and crawled.body:
                try:
                    storage_path = storage.put_html(audit_id, page_id, crawled.body)
                except Exception:
                    logger.warning("html_store_failed", url=snapshot.final_url)
            db.add(
                Page(
                    id=page_id,
                    audit_id=audit_id,
                    position=position,
                    url=snapshot.url,
                    final_url=snapshot.final_url,
                    status_code=snapshot.status_code,
                    title=snapshot.title,
                    meta_description=snapshot.meta_description,
                    content_hash=snapshot.content_hash or None,
                    html_storage_path=storage_path,
                    extract={
                        "redirect_count": snapshot.redirect_count,
                        "redirect_loop": snapshot.redirect_loop,
                        "canonical": snapshot.canonical,
                        "canonical_count": snapshot.canonical_count,
                        "h1": list(snapshot.h1),
                        "word_count": snapshot.word_count,
                        "meta_robots": snapshot.meta_robots,
                        "header_robots": snapshot.header_robots,
                        "is_html": snapshot.is_html,
                        "script_count": snapshot.script_count,
                        "error": snapshot.error,
                    },
                )
            )
        for item in checks:
            if item.status == "pass":
                continue
            db.add(
                Issue(
                    audit_id=audit_id,
                    check_id=item.check_id,
                    severity=item.severity,
                    title=item.title,
                    description=item.description,
                    recommendation=item.recommendation,
                    affected_urls=list(item.affected_urls),
                    status=item.status,
                    quick_win=item.quick_win,
                )
            )
        by_category: dict[str, float] = {}
        for item in scores:
            if item.score is None:
                continue
            by_category[item.category] = item.score
            db.add(Score(audit_id=audit_id, category=item.category, score=item.score, details=item.details))
        audit.pages_crawled = len(snapshots)
        audit.overall_score = by_category.get("overall")
        audit.seo_score = by_category.get("seo")
        audit.geo_score = by_category.get("geo")
        audit.status = "completed"
        audit.finished_at = datetime.now(timezone.utc)
        audit.error_message = None
        db.commit()


def _mark_failed(audit_id: UUID, message: str) -> None:
    try:
        with session_scope() as db:
            audit = db.get(Audit, audit_id)
            if audit is None:
                return
            audit.status = "failed"
            audit.error_message = message[:2000]
            audit.finished_at = datetime.now(timezone.utc)
            db.commit()
    except Exception:
        logger.exception("audit_failure_not_stored", audit_id=str(audit_id))
