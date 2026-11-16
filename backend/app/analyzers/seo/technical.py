"""Technical SEO checks T01–T05, T07, T08, T11, and T14."""

from __future__ import annotations

from urllib.parse import urlsplit

from app.analyzers.common import Spec, result
from app.crawler.robots import RobotsPolicy
from app.crawler.urls import crawl_key, document_key, same_site
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
T07 = Spec(
    "T07",
    "critical",
    "HTTPS",
    "Die ganze Website über HTTPS ausliefern und keine HTTP-Ressourcen in HTTPS-Seiten einbinden.",
)
T08 = Spec(
    "T08",
    "high",
    "Viewport",
    'Ein Viewport-Meta mit width=device-width setzen, zum Beispiel content="width=device-width, initial-scale=1".',
    quick_win=True,
)
T11 = Spec(
    "T11",
    "high",
    "JavaScript-Abhängigkeit",
    "Den zentralen Inhalt bereits im ersten HTML ausgeben, nicht erst nach dem Ausführen von Skripten.",
)
T14 = Spec(
    "T14",
    "high",
    "Defekte interne Links",
    "Interne Links, die auf Fehlerseiten zeigen, auf ein erreichbares Ziel ändern oder entfernen.",
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
    if document_key(page.canonical) == document_key(target):
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


def check_https(page: PageSnapshot) -> CheckResult:
    """T07: the final URL is HTTPS and embeds no HTTP resources."""

    url = page.final_url or page.url
    if urlsplit(url).scheme != "https":
        return result(T07, "fail", "Die Seite wird nicht über HTTPS ausgeliefert.", (url,))
    if page.insecure_resources:
        sample = ", ".join(page.insecure_resources[:3])
        return result(
            T07,
            "fail",
            f"Die HTTPS-Seite bindet unsichere HTTP-Ressourcen ein: {sample}.",
            (url,),
        )
    return result(T07, "pass", "Die geprüften Seiten laufen über HTTPS ohne gemischte Inhalte.")


def check_viewport(page: PageSnapshot) -> CheckResult:
    """T08: a viewport meta sets the device width."""

    if not page.viewport:
        return result(T08, "fail", "Das Viewport-Meta fehlt.", (page.final_url,))
    if "width=device-width" in page.viewport.replace(" ", "").lower():
        return result(T08, "pass", "Das Viewport-Meta setzt width=device-width.")
    return result(
        T08,
        "warning",
        f"Das Viewport-Meta nennt keine Gerätebreite: {page.viewport}.",
        (page.final_url,),
    )


def check_javascript(page: PageSnapshot) -> CheckResult:
    """T11: important copy is already in the first HTML response."""

    if page.script_count < 5 or page.word_count >= 80:
        return result(T11, "pass", "Wichtige Inhalte stehen bereits im ersten HTML.")
    url = (page.final_url,)
    text = f"Bei {page.script_count} Skripten stehen nur {page.word_count} Wörter im Roh-HTML."
    if page.rendered_word_count is not None and page.rendered_word_count >= 80:
        text = f"{text} Nach dem Rendern sind {page.rendered_word_count} Wörter sichtbar."
    if page.word_count < 40:
        return result(T11, "fail", text, url)
    return result(T11, "warning", text, url)


def check_broken_links(context: SiteContext) -> CheckResult | None:
    """T14: internal links must not end on an error status."""

    if not context.pages:
        return None
    fetched = {crawl_key(page.final_url): page for page in context.pages}
    probed = context.link_status
    broken: list[str] = []
    checked = 0
    for page in context.pages:
        for link in page.links:
            if not same_site(page.final_url, link):
                continue
            key = crawl_key(link)
            target = fetched.get(key)
            if target is not None:
                status = target.status_code
            elif key in probed:
                status = probed[key]
            else:
                continue
            if status is None:
                continue
            checked += 1
            if status != 0 and status < 400:
                continue
            if link not in broken:
                broken.append(link)
    if checked == 0:
        return None
    if not broken:
        return result(T14, "pass", "Interne Links führen auf keine bekannte Fehlerseite.")
    count = len(broken)
    return result(T14, "fail", f"{count} interne Ziele antworten mit einem Fehler.", tuple(broken))


def page_has_noindex(page: PageSnapshot) -> bool:
    """True when meta robots or the X-Robots-Tag asks not to index."""

    return _has_noindex(page.meta_robots, page.header_robots)


def _has_noindex(*values: str | None) -> bool:
    for value in values:
        if not value:
            continue
        for part in value.replace(";", ",").split(","):
            token = part.strip().lower()
            if ":" in token:
                token = token.split(":", 1)[1].strip()
            if token in {"noindex", "none"}:
                return True
    return False
