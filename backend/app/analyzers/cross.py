"""Cross-cutting check X01."""

from __future__ import annotations

from itertools import pairwise

from app.analyzers.common import Spec, result
from app.analyzers.seo.technical import page_has_noindex
from app.crawler.robots import RobotsPolicy
from app.crawler.urls import document_key
from app.domain import CheckResult, PageSnapshot, SiteContext

X01 = Spec(
    "X01",
    "critical",
    "Indexierbarkeit",
    "Statuscode, robots.txt, Canonical und noindex so setzen, dass wichtige Seiten aufgenommen werden können.",
)


X02 = Spec(
    "X02",
    "medium",
    "Sicherheitsheader",
    "HSTS, eine Content-Security-Policy und X-Content-Type-Options: nosniff setzen.",
)
X03 = Spec(
    "X03",
    "low",
    "Basis-Barrierefreiheit",
    "Bilder mit alt-Attribut auszeichnen und Überschriften ohne Sprung staffeln.",
)
X04 = Spec(
    "X04",
    "medium",
    "Inhaltliche Qualität",
    "Einen erkennbaren Aufbau liefern: Überschrift, mehrere Absätze und genug Text, nicht nur ein Satz.",
)


def check_security_headers(context: SiteContext) -> CheckResult | None:
    """X02: the crawled HTML responses carry the basic hardening headers."""

    pages = [page for page in context.pages if page.is_html and 200 <= page.status_code < 300]
    if not pages:
        return None
    missing = [
        page.final_url
        for page in pages
        if not (page.hsts and page.content_security_policy and page.content_type_options)
    ]
    if not missing:
        return result(X02, "pass", "HSTS, Content-Security-Policy und nosniff sind gesetzt.")
    if len(missing) == len(pages):
        return result(X02, "fail", "Die grundlegenden Sicherheitsheader fehlen.", tuple(missing))
    return result(X02, "warning", "Nicht jede Seite liefert die Sicherheitsheader.", tuple(missing))


def check_accessibility(context: SiteContext) -> CheckResult | None:
    """X03: images and headings cover the basic accessibility overlap."""

    pages = [page for page in context.pages if page.is_html and 200 <= page.status_code < 300]
    if not pages:
        return None
    weak = [page.final_url for page in pages if page.images_missing_alt or _weak_headings(page.heading_levels)]
    if not weak:
        return result(X03, "pass", "Bilder und Überschriften erfüllen die Basisprüfung.")
    if len(weak) == len(pages):
        return result(X03, "fail", "Alternativtexte oder die Überschriftenstruktur fehlen.", tuple(weak))
    return result(X03, "warning", "Ein Teil der Seiten schwächelt bei Alternativtext oder Überschriften.", tuple(weak))


def _weak_headings(levels: tuple[int, ...]) -> bool:
    if not levels or levels[0] != 1:
        return True
    return any(current > previous + 1 for previous, current in pairwise(levels))


def check_content_quality(page: PageSnapshot) -> CheckResult:
    """X04: structure and length together, distinct from a single word-count check."""

    paragraphs = len(page.paragraph_words)
    if page.word_count >= 250 and paragraphs >= 2 and page.heading_levels:
        return result(X04, "pass", "Überschrift, Absätze und Textumfang tragen die Seite.")
    if page.word_count >= 80 and (paragraphs >= 1 or page.heading_levels):
        return result(X04, "warning", "Der Aufbau ist erkennbar, der Text bleibt aber dünn.", (page.final_url,))
    return result(X04, "fail", "Die Seite wirkt dünn: wenig Text und kaum Struktur.", (page.final_url,))


def check_indexability(context: SiteContext) -> CheckResult:
    """X01: status, robots, canonical, and noindex agree on indexable pages."""

    if not context.pages:
        return result(
            X01,
            "fail",
            "Ohne gelesene Seite ist die Indexierung nicht belegbar.",
            (context.start_url,),
        )
    policy = RobotsPolicy(context.robots_txt, context.robots_status)
    blocked: list[str] = []
    redirected_canonical: list[str] = []
    for page in context.pages:
        url = page.final_url or page.url
        if _hard_block(page, policy, context.user_agent, url):
            blocked.append(url)
        elif _foreign_canonical(page, url):
            redirected_canonical.append(url)
    if blocked:
        return result(
            X01,
            "fail",
            f"{len(blocked)} Seiten sind wegen Status, noindex oder robots.txt nicht indexierbar.",
            tuple(dict.fromkeys(blocked)),
        )
    if redirected_canonical:
        return result(
            X01,
            "warning",
            "Der Canonical zeigt auf eine andere URL als die ausgelieferte Seite.",
            tuple(dict.fromkeys(redirected_canonical)),
        )
    return result(X01, "pass", "Status, robots.txt und Indexierungsanweisung lassen die geprüften Seiten zu.")


def _hard_block(page: PageSnapshot, policy: RobotsPolicy, user_agent: str, url: str) -> bool:
    if page.error or not (200 <= page.status_code < 300):
        return True
    if page_has_noindex(page):
        return True
    return bool(policy.body.strip()) and not policy.allowed(user_agent, url)


def _foreign_canonical(page: PageSnapshot, url: str) -> bool:
    if not page.canonical:
        return False
    return document_key(page.canonical) != document_key(url)
