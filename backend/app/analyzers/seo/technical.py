"""Technical SEO checks T01–T05."""

from __future__ import annotations

from app.analyzers.common import Spec, result
from app.crawler.robots import RobotsPolicy
from app.crawler.urls import crawl_key
from app.domain import CheckResult, PageSnapshot, SiteContext

T01 = Spec(
    "T01",
    "critical",
    "HTTP-Status",
    "Indexierbare Seiten müssen mit HTTP 200 antworten. Fehlerseiten und defekte Ziele auf eine erreichbare URL führen oder aus der Navigation nehmen.",
)
T02 = Spec(
    "T02",
    "high",
    "Weiterleitungsketten",
    "Höchstens eine Weiterleitung bis zum Ziel lassen. Ketten und Schleifen auf eine direkte URL kürzen.",
)
T03 = Spec(
    "T03",
    "high",
    "Canonical",
    "Jede indexierbare Seite braucht genau einen Canonical, der auf die bevorzugte URL zeigt.",
    quick_win=True,
)
T04 = Spec(
    "T04",
    "critical",
    "Indexierungsanweisung",
    "noindex nur auf Seiten setzen, die bewusst nicht in den Index gehören. Wichtige Seiten ohne noindex ausliefern.",
    quick_win=True,
)
T05 = Spec(
    "T05",
    "high",
    "robots.txt",
    "Eine erreichbare robots.txt anlegen, die wichtige Pfade erlaubt und die Sitemap nennt.",
    quick_win=True,
)


def check_status_code(page: PageSnapshot) -> CheckResult:
    """T01: indexable URLs answer with HTTP 200."""

    if page.error or page.status_code == 0:
        description = page.error or "Die Seite konnte nicht geladen werden."
        return result(T01, "fail", description, (page.final_url,))
    if 200 <= page.status_code < 300:
        return result(T01, "pass", "Alle geprüften Seiten antworten mit einem erfolgreichen HTTP-Status.")
    return result(
        T01,
        "fail",
        f"Die Seite antwortet mit HTTP {page.status_code}.",
        (page.final_url,),
    )


def check_redirects(page: PageSnapshot) -> CheckResult:
    """T02: at most one redirect, and no loops."""

    if page.redirect_loop:
        return result(T02, "fail", "Die Weiterleitung läuft im Kreis.", (page.final_url,))
    if page.redirect_count > 1:
        return result(
            T02,
            "fail",
            f"Die URL hat {page.redirect_count} Weiterleitungen. Zulässig ist höchstens eine.",
            (page.url,),
        )
    return result(T02, "pass", "Es gibt keine Weiterleitungskette.")


def check_canonical(page: PageSnapshot) -> CheckResult:
    """T03: one self-referencing or otherwise deliberate canonical."""

    target = page.final_url
    if page.canonical_count > 1:
        return result(T03, "fail", "Mehrere Canonical-Tags widersprechen sich.", (target,))
    if page.canonical_count == 0:
        return result(T03, "warning", "Es fehlt ein Canonical-Tag.", (target,))
    if not page.canonical:
        return result(T03, "fail", "Der Canonical-Tag hat kein Ziel.", (target,))
    if crawl_key(page.canonical) == crawl_key(target):
        return result(T03, "pass", "Der Canonical zeigt auf die Seite selbst.")
    return result(
        T03,
        "warning",
        f"Der Canonical zeigt auf eine andere URL: {page.canonical}",
        (target,),
    )


def check_noindex(page: PageSnapshot) -> CheckResult:
    """T04: important pages are not marked noindex."""

    if _has_noindex(page.meta_robots, page.header_robots):
        return result(
            T04,
            "fail",
            "Die Seite ist per noindex von der Indexierung ausgeschlossen.",
            (page.final_url,),
        )
    return result(T04, "pass", "Keine unerwünschte noindex-Anweisung gefunden.")


def check_robots_txt(context: SiteContext) -> CheckResult:
    """T05: robots.txt exists, allows the start URL, and names a sitemap."""

    policy = RobotsPolicy(context.robots_txt, context.robots_status)
    if policy.unreadable:
        return result(
            T05,
            "fail",
            "robots.txt war nicht erreichbar. Wichtige Pfade lassen sich so nicht freigeben.",
            (context.start_url,),
        )
    if not policy.exists:
        return result(T05, "fail", "robots.txt fehlt.", (context.start_url,))
    blocked = not policy.allowed(context.user_agent, context.start_url)
    has_sitemap = bool(policy.sitemaps())
    if blocked:
        extra = "" if has_sitemap else " Außerdem fehlt die Angabe einer Sitemap."
        return result(
            T05,
            "fail",
            f"robots.txt verbietet die Start-URL.{extra}",
            (context.start_url,),
        )
    if not has_sitemap:
        return result(
            T05,
            "warning",
            "robots.txt erlaubt die Start-URL, nennt aber keine Sitemap.",
            (context.start_url,),
        )
    return result(T05, "pass", "robots.txt erlaubt die Start-URL und nennt eine Sitemap.")


def _has_noindex(*values: str | None) -> bool:
    tokens: list[str] = []
    for value in values:
        if not value:
            continue
        tokens.extend(part.strip().lower() for part in value.replace(";", ",").split(","))
    return "noindex" in tokens or "none" in tokens
