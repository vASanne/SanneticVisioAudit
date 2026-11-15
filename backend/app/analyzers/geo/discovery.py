"""GEO checks G01 and G04."""

from __future__ import annotations

from app.analyzers.common import Spec, result
from app.crawler.robots import RobotsPolicy
from app.domain import CheckResult, PageSnapshot, SiteContext

AI_SEARCH_BOTS = ("OAI-SearchBot", "PerplexityBot", "Claude-SearchBot", "Google-Extended")

G01 = Spec(
    "G01",
    "critical",
    "Zugriff für AI-Suchmaschinen",
    "OAI-SearchBot, PerplexityBot, Claude-SearchBot und Google-Extended in robots.txt ausdrücklich erlauben. Trainings-Bots wie GPTBot können davon getrennt eingeschränkt werden.",
    quick_win=True,
)
G04 = Spec(
    "G04",
    "critical",
    "Serverseitiger Inhalt",
    "Wichtige Inhalte im Roh-HTML ausgeben, sodass Suchmaschinen und AI-Crawler sie ohne JavaScript lesen können.",
)

_JS_RECOMMENDATION = (
    "Den Kerninhalt bereits im ersten HTML ausliefern, nicht erst per JavaScript. "
    "Ein späteres Browser-Rendering kann die Darstellung prüfen, ersetzt aber keinen serverseitigen Text."
)


def check_ai_crawlers(context: SiteContext) -> CheckResult:
    """G01: search-oriented AI crawlers may fetch the start URL."""

    policy = RobotsPolicy(context.robots_txt, context.robots_status)
    if policy.unreadable:
        return result(
            G01,
            "warning",
            "robots.txt war nicht lesbar. Der Zugriff der AI-Such-Bots konnte nicht bestätigt werden.",
            (context.start_url,),
        )
    if not policy.body.strip():
        return result(
            G01,
            "pass",
            "Es gibt keine robots.txt. AI-Such-Bots sind damit standardmäßig erlaubt.",
        )
    blocked = [bot for bot in AI_SEARCH_BOTS if not policy.allowed(bot, context.start_url)]
    if blocked:
        names = ", ".join(blocked)
        return result(
            G01,
            "fail",
            f"Diese AI-Such-Bots werden blockiert: {names}.",
            (context.start_url,),
        )
    return result(
        G01,
        "pass",
        "OAI-SearchBot, PerplexityBot, Claude-SearchBot und Google-Extended dürfen die Start-URL lesen.",
    )


def check_server_rendered(page: PageSnapshot) -> CheckResult:
    """G04: the initial HTML already contains the core copy."""

    if page.word_count >= 80:
        return result(G04, "pass", "Der sichtbare Text steht im Roh-HTML.")
    description = f"Im Roh-HTML stehen nur {page.word_count} Wörter."
    recommendation = _JS_RECOMMENDATION if page.script_count >= 5 and page.word_count < 40 else None
    if page.word_count >= 40:
        return result(G04, "warning", description, (page.final_url,), recommendation)
    return result(G04, "fail", description, (page.final_url,), recommendation)
