"""Run the implemented checks and collapse page results into one finding per check.

Covered now: T01–T15 except T09 unless a PageSpeed key is configured, O01–O10,
G01–G14, and X01–X04. Checks that are not run are omitted and are not counted
as passed.
"""

from __future__ import annotations

from collections.abc import Callable

from app.analyzers.cross import (
    check_accessibility,
    check_content_quality,
    check_indexability,
    check_security_headers,
)
from app.analyzers.geo.content import (
    check_answer_first,
    check_citability,
    check_entity_clarity,
    check_experience,
    check_extractable,
    check_faq,
    check_freshness,
    check_statistics,
)
from app.analyzers.geo.discovery import (
    check_ai_crawlers,
    check_ai_discovery,
    check_entity_schema,
    check_llms_txt,
    check_server_rendered,
    check_training_split,
)
from app.analyzers.performance import check_pagespeed
from app.analyzers.seo.content import (
    check_content_length,
    check_headings,
    check_image_alt,
    check_keyword_use,
    check_social_tags,
)
from app.analyzers.seo.extended import (
    check_duplicates,
    check_hreflang,
    check_html_size,
    check_internal_links,
    check_sitemap,
)
from app.analyzers.seo.onpage import (
    check_h1,
    check_meta_description,
    check_schema_validity,
    check_structured_data,
    check_title,
)
from app.analyzers.seo.technical import (
    check_broken_links,
    check_canonical,
    check_https,
    check_javascript,
    check_noindex,
    check_redirects,
    check_robots_txt,
    check_status_code,
    check_viewport,
)
from app.domain import CheckResult, PageSnapshot, SiteContext

PageCheck = Callable[[PageSnapshot], CheckResult | None]

_ALWAYS: tuple[PageCheck, ...] = (check_status_code, check_redirects, check_https)
_HTML_200: tuple[PageCheck, ...] = (
    check_html_size,
    check_canonical,
    check_noindex,
    check_viewport,
    check_javascript,
    check_title,
    check_meta_description,
    check_h1,
    check_headings,
    check_image_alt,
    check_content_length,
    check_social_tags,
    check_structured_data,
    check_schema_validity,
    check_keyword_use,
    check_server_rendered,
    check_answer_first,
    check_extractable,
    check_statistics,
    check_entity_clarity,
    check_faq,
    check_freshness,
    check_experience,
    check_content_quality,
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
    results.append(check_sitemap(context))
    results.append(check_training_split(context))
    results.append(check_llms_txt(context))
    results.append(check_ai_discovery(context))
    broken = check_broken_links(context)
    if broken is not None:
        results.append(broken)
    links = check_internal_links(context)
    if links is not None:
        results.append(links)
    hreflang = check_hreflang(context)
    if hreflang is not None:
        results.append(hreflang)
    duplicates = check_duplicates(context)
    if duplicates is not None:
        results.append(duplicates)
    results.append(check_indexability(context))
    headers = check_security_headers(context)
    if headers is not None:
        results.append(headers)
    access = check_accessibility(context)
    if access is not None:
        results.append(access)
    results.append(check_entity_schema(context))
    speed = check_pagespeed(context)
    if speed is not None:
        results.append(speed)
    citability = check_citability(results)
    if citability is not None:
        results.append(citability)
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
        recommendation=_recommendation(chosen),
        affected_urls=urls,
        quick_win=sample.quick_win,
    )


def _recommendation(chosen: list[CheckResult]) -> str:
    """Keep a page-specific recommendation when failures do not share one text."""

    unique = list(dict.fromkeys(item.recommendation for item in chosen if item.recommendation))
    if len(unique) < 2:
        return unique[0] if unique else chosen[0].recommendation
    return f"{unique[0]} {unique[1]}"


def _collect(grouped: dict[str, list[CheckResult]], item: CheckResult | None) -> None:
    if item is None:
        return
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
