"""Run the MVP check set and collapse page results into one finding per check.

Implemented now, matching the first implementation step in the specification:
T01–T05, O01–O03, G01, and G04. The remaining checks in section 3 are not scored
and are not treated as passed.
"""

from __future__ import annotations

from collections.abc import Callable

from app.analyzers.geo.discovery import check_ai_crawlers, check_server_rendered
from app.analyzers.seo.onpage import check_h1, check_meta_description, check_title
from app.analyzers.seo.technical import (
    check_canonical,
    check_noindex,
    check_redirects,
    check_robots_txt,
    check_status_code,
)
from app.domain import CheckResult, PageSnapshot, SiteContext

PageCheck = Callable[[PageSnapshot], CheckResult]

_ALWAYS: tuple[PageCheck, ...] = (check_status_code, check_redirects)
_HTML_200: tuple[PageCheck, ...] = (
    check_canonical,
    check_noindex,
    check_title,
    check_meta_description,
    check_h1,
    check_server_rendered,
)


def run_checks(context: SiteContext) -> list[CheckResult]:
    """Evaluate every implemented check against the crawl."""

    grouped: dict[str, list[CheckResult]] = {}
    for page in context.pages:
        for check in _ALWAYS:
            _collect(grouped, check(page))
        if _indexable_html(page):
            for check in _HTML_200:
                _collect(grouped, check(page))

    results = [aggregate(items) for items in grouped.values()]
    if context.blocked_by_robots and not context.pages:
        results.append(_blocked_start(context))
    results.append(check_robots_txt(context))
    results.append(check_ai_crawlers(context))
    return results


def aggregate(results: list[CheckResult]) -> CheckResult:
    """Collapse per-page results. Any failure wins over a warning."""

    if len(results) == 1:
        return results[0]
    fails = [item for item in results if item.status == "fail"]
    warnings = [item for item in results if item.status == "warning"]
    chosen = fails or warnings
    if not chosen:
        return results[0]
    sample = chosen[0]
    urls = tuple(dict.fromkeys(url for item in chosen for url in item.affected_urls))
    descriptions = list(dict.fromkeys(item.description for item in chosen))
    summary = descriptions[0]
    if len(chosen) > 1:
        summary = f"{len(chosen)} von {len(results)} Seiten. {summary}"
    if len(descriptions) > 1:
        summary = f"{summary} Weitere Abweichung: {descriptions[1]}"
    return CheckResult(
        check_id=sample.check_id,
        status="fail" if fails else "warning",
        severity=sample.severity,
        title=sample.title,
        description=summary,
        recommendation=sample.recommendation,
        affected_urls=urls,
        quick_win=sample.quick_win,
    )


def _collect(grouped: dict[str, list[CheckResult]], item: CheckResult) -> None:
    grouped.setdefault(item.check_id, []).append(item)


def _indexable_html(page: PageSnapshot) -> bool:
    return page.is_html and 200 <= page.status_code < 300


def _blocked_start(context: SiteContext) -> CheckResult:
    return CheckResult(
        check_id="T01",
        status="fail",
        severity="critical",
        title="HTTP-Status",
        description="Die Start-URL ist in robots.txt für den Crawler gesperrt, deshalb liegt kein HTTP-Status vor.",
        recommendation="Die Start-URL für prüfende Bots erlauben oder die Sperre auf wirklich private Pfade begrenzen.",
        affected_urls=(context.start_url,),
    )
