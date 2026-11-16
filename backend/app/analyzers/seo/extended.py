"""Technical checks T06, T10, T12, T13, and T15."""

from __future__ import annotations

import re
from collections.abc import Callable
from urllib.parse import urlsplit

from app.analyzers.common import Spec, result
from app.analyzers.seo.technical import page_has_noindex
from app.crawler.robots import RobotsPolicy
from app.crawler.urls import same_site
from app.domain import CheckResult, PageSnapshot, SiteContext

T06 = Spec(
    "T06",
    "medium",
    "XML-Sitemap",
    "Eine erreichbare XML-Sitemap mit den aktuellen URLs in robots.txt nennen.",
)
T10 = Spec(
    "T10",
    "medium",
    "HTML-Größe",
    "Überflüssiges Markup, eingebettete Daten und ungenutzte Blöcke aus dem HTML nehmen.",
)
T12 = Spec(
    "T12",
    "medium",
    "Hreflang",
    "Jedes hreflang braucht einen Sprachcode und eine absolute URL. x-default deckt die Fallback-Sprache ab.",
)
T13 = Spec(
    "T13",
    "medium",
    "Interne Verlinkung",
    "Wichtige Seiten von anderen Seiten der Website verlinken, damit keine URL ohne Eingang bleibt.",
)
T15 = Spec(
    "T15",
    "medium",
    "Doppelte Titles und Descriptions",
    "Jeder indexierbaren Seite einen eigenen Title und eine eigene Meta-Description geben.",
)

_LANG = re.compile(r"^[a-z]{2,3}(-[a-z0-9]+)*$", re.IGNORECASE)


def check_sitemap(context: SiteContext) -> CheckResult:
    """T06: a declared sitemap answers with XML that lists URLs."""

    policy = RobotsPolicy(context.robots_txt, context.robots_status)
    if not policy.sitemaps():
        return result(T06, "warning", "robots.txt nennt keine Sitemap.", (context.start_url,))
    if context.sitemap_status != 200:
        return result(T06, "fail", "Die in robots.txt genannte Sitemap war nicht erreichbar.", (context.start_url,))
    if context.sitemap_count is None:
        return result(T06, "fail", "Die Sitemap-Antwort ist kein XML-Sitemap.", (context.start_url,))
    if context.sitemap_count < 1:
        return result(T06, "warning", "Die Sitemap enthält keine URLs.", (context.start_url,))
    return result(T06, "pass", f"Die Sitemap nennt {context.sitemap_count} Adressen.")


def check_html_size(page: PageSnapshot) -> CheckResult:
    """T10: the raw document stays in a reasonable size."""

    kilo = max(1, round(page.html_bytes / 1000))
    if page.html_bytes <= 500_000:
        return result(T10, "pass", "Die HTML-Dokumente bleiben in einem üblichen Rahmen.")
    if page.html_bytes <= 1_500_000:
        return result(T10, "warning", f"Das HTML ist mit etwa {kilo} KB groß.", (page.final_url,))
    return result(T10, "fail", f"Das HTML ist mit etwa {kilo} KB aufgebläht.", (page.final_url,))


def check_hreflang(context: SiteContext) -> CheckResult | None:
    """T12: evaluate hreflang only when a page publishes it."""

    pages = [page for page in context.pages if page.is_html and page.hreflang]
    if not pages:
        return None
    broken: list[str] = []
    missing_default = True
    for page in pages:
        if any(code.lower() == "x-default" for code in page.hreflang):
            missing_default = False
        if _bad_hreflang(page):
            broken.append(page.final_url)
    if broken:
        return result(
            T12,
            "fail",
            "Mindestens ein hreflang ist kein Sprachcode oder keine absolute URL.",
            tuple(broken),
        )
    if missing_default:
        return result(
            T12,
            "warning",
            "Hreflang ist gesetzt, x-default fehlt.",
            tuple(page.final_url for page in pages),
        )
    return result(T12, "pass", "Die hreflang-Angaben nutzen Sprachcodes und x-default.")


def check_internal_links(context: SiteContext) -> CheckResult | None:
    """T13: HTML pages should link to other pages on the same site."""

    pages = [page for page in context.pages if page.is_html and 200 <= page.status_code < 300]
    if len(pages) < 2:
        return result(T13, "pass", "Bei einer einzelnen Seite gibt es keine interne Verlinkung zu prüfen.") if pages else None
    lonely = [
        page.final_url
        for page in pages
        if not any(same_site(page.final_url, link) for link in page.links)
    ]
    if not lonely:
        return result(T13, "pass", "Die gelesenen Seiten verlinken innerhalb der Website.")
    if len(lonely) * 2 >= len(pages):
        return result(T13, "fail", f"{len(lonely)} Seiten haben keinen internen Link.", tuple(lonely))
    return result(T13, "warning", f"{len(lonely)} Seiten haben keinen internen Link.", tuple(lonely))


def check_duplicates(context: SiteContext) -> CheckResult | None:
    """T15: titles and meta descriptions are not repeated across indexable URLs."""

    pages = [page for page in context.pages if _indexable(page)]
    if not pages:
        return None
    title_hits = _repeated(pages, lambda page: (page.title or "").casefold())
    description_hits = _repeated(pages, lambda page: (page.meta_description or "").casefold())
    urls = tuple(dict.fromkeys((*title_hits, *description_hits)))
    if not urls:
        return result(T15, "pass", "Titles und Meta-Descriptions unterscheiden sich.")
    kind = "Titles" if title_hits else "Meta-Descriptions"
    if title_hits and description_hits:
        kind = "Titles und Meta-Descriptions"
    return result(T15, "fail", f"{kind} kommen auf mehreren Seiten gleichlautend vor.", urls)


def _bad_hreflang(page: PageSnapshot) -> bool:
    hrefs = page.hreflang_hrefs
    if len(hrefs) != len(page.hreflang):
        return True
    for code, href in zip(page.hreflang, hrefs, strict=True):
        if code.lower() != "x-default" and _LANG.match(code) is None:
            return True
        parts = urlsplit(href)
        if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
            return True
    return False


def _indexable(page: PageSnapshot) -> bool:
    return page.is_html and 200 <= page.status_code < 300 and not page_has_noindex(page)


def _repeated(pages: list[PageSnapshot], value: Callable[[PageSnapshot], str]) -> list[str]:
    groups: dict[str, list[str]] = {}
    for page in pages:
        text = value(page)
        if len(text) < 5:
            continue
        groups.setdefault(text, []).append(page.final_url)
    return [url for urls in groups.values() if len(urls) > 1 for url in urls]
