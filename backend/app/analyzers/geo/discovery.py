"""GEO checks G01, G04, and G09."""

from __future__ import annotations

from app.analyzers.common import Spec, result
from app.crawler.robots import RobotsPolicy
from app.domain import CheckResult, PageSnapshot, SiteContext

AI_SEARCH_BOTS = ("OAI-SearchBot", "PerplexityBot", "Claude-SearchBot", "Google-Extended")

G01 = Spec(
    "G01",
    "critical",
    "Zugriff für AI-Suchmaschinen",
    (
        "OAI-SearchBot, PerplexityBot, Claude-SearchBot und Google-Extended in robots.txt "
        "ausdrücklich erlauben. Trainings-Bots wie GPTBot können davon getrennt eingeschränkt werden."
    ),
    quick_win=True,
)
G04 = Spec(
    "G04",
    "critical",
    "Serverseitiger Inhalt",
    "Wichtige Inhalte im Roh-HTML ausgeben, sodass Suchmaschinen und AI-Crawler sie ohne JavaScript lesen können.",
)
G09 = Spec(
    "G09",
    "high",
    "Schema für Entitäten",
    "Organization oder WebSite als JSON-LD hinterlegen, damit AI-Systeme die Marke eindeutig zuordnen.",
)

_ENTITY_TYPES = {"organization", "website", "localbusiness", "corporation"}

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


G02 = Spec(
    "G02",
    "medium",
    "Training und Suche trennen",
    "Such-Bots wie OAI-SearchBot erlauben und Trainings-Bots wie GPTBot in einer eigenen Gruppe einschränken.",
)
G03 = Spec(
    "G03",
    "medium",
    "llms.txt",
    "Unter /llms.txt in kurzen Abschnitten erklären, welche Inhalte ein Sprachmodell zitieren soll.",
)
G13 = Spec(
    "G13",
    "low",
    "KI-Entdeckungsdateien",
    "llms.txt oder ai.txt bereitlegen, damit Systeme die Website gezielt finden.",
)

_TRAINING_BOTS = ("GPTBot", "ClaudeBot", "CCBot")


def check_training_split(context: SiteContext) -> CheckResult:
    """G02: search bots stay allowed while at least one training bot is limited."""

    policy = RobotsPolicy(context.robots_txt, context.robots_status)
    if policy.unreadable or not policy.body.strip():
        return result(
            G02,
            "warning",
            "Ohne lesbare robots.txt ist die Trennung von Training und Suche nicht festgelegt.",
            (context.start_url,),
        )
    blocked_search = [bot for bot in AI_SEARCH_BOTS if not policy.allowed(bot, context.start_url)]
    if blocked_search:
        return result(G02, "fail", f"Such-Bots sind blockiert: {', '.join(blocked_search)}.", (context.start_url,))
    blocked_training = [bot for bot in _TRAINING_BOTS if not policy.allowed(bot, context.start_url)]
    if blocked_training:
        return result(G02, "pass", f"Such-Bots dürfen lesen. Eingeschränkt: {', '.join(blocked_training)}.")
    return result(G02, "warning", "Trainings-Bots wie GPTBot sind nicht getrennt eingeschränkt.", (context.start_url,))


def check_llms_txt(context: SiteContext) -> CheckResult:
    """G03: /llms.txt exists and contains usable guidance."""

    if context.llms_status != 200:
        return result(G03, "warning", "llms.txt fehlt oder war nicht erreichbar.", (context.start_url,))
    if context.llms_words < 40:
        return result(G03, "warning", f"llms.txt enthält nur {context.llms_words} Wörter.", (context.start_url,))
    return result(G03, "pass", "llms.txt ist erreichbar und enthält eine nutzbare Beschreibung.")


def check_ai_discovery(context: SiteContext) -> CheckResult:
    """G13: llms.txt or ai.txt gives AI systems a discovery file."""

    if context.llms_status == 200 or context.ai_txt_status == 200:
        return result(G13, "pass", "Eine Entdeckungsdatei für KI-Systeme ist erreichbar.")
    return result(G13, "warning", "Weder llms.txt noch ai.txt waren erreichbar.", (context.start_url,))


def check_entity_schema(context: SiteContext) -> CheckResult:
    """G09: the crawl publishes an Organization or WebSite entity."""

    found: set[str] = set()
    for page in context.pages:
        for block in page.json_ld:
            if block.valid_json:
                found.update(item.lower() for item in block.types)
    if found & _ENTITY_TYPES:
        return result(G09, "pass", "Organization oder WebSite ist als Schema hinterlegt.")
    if found:
        return result(
            G09,
            "warning",
            "Es gibt Schema, aber weder Organization noch WebSite.",
            (context.start_url,),
        )
    return result(G09, "fail", "Organization- oder WebSite-Schema fehlt.", (context.start_url,))


def check_server_rendered(page: PageSnapshot) -> CheckResult:
    """G04: the initial HTML already contains the core copy."""

    if page.word_count >= 80:
        return result(G04, "pass", "Der sichtbare Text steht im Roh-HTML.")
    description = f"Im Roh-HTML stehen nur {page.word_count} Wörter."
    recommendation = _JS_RECOMMENDATION if page.script_count >= 5 and page.word_count < 40 else None
    if page.word_count >= 40:
        return result(G04, "warning", description, (page.final_url,), recommendation)
    return result(G04, "fail", description, (page.final_url,), recommendation)
