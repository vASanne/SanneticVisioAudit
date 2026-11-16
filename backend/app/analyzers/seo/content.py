"""On-page checks O04–O07 and O10."""

from __future__ import annotations

import re
from collections import Counter

from app.analyzers.common import Spec, result
from app.domain import CheckResult, PageSnapshot

O04 = Spec(
    "O04",
    "medium",
    "Überschriftenstruktur",
    "Überschriften ohne Sprung führen: auf H1 folgt H2, nicht sofort H3.",
)
O05 = Spec(
    "O05",
    "medium",
    "Alternativtexte",
    "Jedem inhaltlichen Bild ein alt-Attribut geben. Dekorative Bilder dürfen alt leer lassen.",
    quick_win=True,
)
O06 = Spec(
    "O06",
    "medium",
    "Textumfang",
    "Für eine inhaltliche Seite genug sichtbaren Text einplanen, als Richtwert mindestens 250 Wörter.",
)
O07 = Spec(
    "O07",
    "low",
    "Social Tags",
    "og:title, og:description und og:image setzen, dazu eine Twitter-Card.",
    quick_win=True,
)
O10 = Spec(
    "O10",
    "low",
    "Keyword-Dichte",
    "Ein Wort nicht über den ganzen Text wiederholen. Lieber konkretisieren als denselben Begriff zu häufen.",
)


def check_headings(page: PageSnapshot) -> CheckResult:
    """O04: heading levels do not skip."""

    levels = page.heading_levels
    if not levels:
        return result(O04, "fail", "Die Seite hat keine Überschriften.", (page.final_url,))
    if levels[0] != 1:
        return result(O04, "warning", "Die erste Überschrift ist keine H1.", (page.final_url,))
    if any(current > previous + 1 for previous, current in zip(levels, levels[1:])):
        return result(O04, "warning", "Die Überschriften überspringen eine Ebene.", (page.final_url,))
    return result(O04, "pass", "Die Überschriften folgen ohne Sprung.")


def check_image_alt(page: PageSnapshot) -> CheckResult:
    """O05: content images expose an alt attribute."""

    if page.images_total == 0:
        return result(O05, "pass", "Es gibt keine Bilder, für die ein Alternativtext fehlt.")
    if page.images_missing_alt:
        return result(
            O05,
            "fail",
            f"{page.images_missing_alt} von {page.images_total} Bildern haben kein alt-Attribut.",
            (page.final_url,),
        )
    if page.images_empty_alt:
        return result(
            O05,
            "warning",
            f"{page.images_empty_alt} von {page.images_total} Bildern haben ein leeres alt-Attribut.",
            (page.final_url,),
        )
    return result(O05, "pass", "Die Bilder haben ein alt-Attribut.")


def check_content_length(page: PageSnapshot) -> CheckResult:
    """O06: the page has enough visible text for its likely intent."""

    if page.word_count >= 250:
        return result(O06, "pass", "Der sichtbare Textumfang reicht für eine inhaltliche Seite.")
    text = f"Im sichtbaren Text stehen {page.word_count} Wörter."
    if page.word_count >= 80:
        return result(O06, "warning", text, (page.final_url,))
    return result(O06, "fail", text, (page.final_url,))


def check_social_tags(page: PageSnapshot) -> CheckResult:
    """O07: Open Graph title, description, and image are present."""

    present = [name for name, value in (("Titel", page.og_title), ("Beschreibung", page.og_description), ("Bild", page.og_image)) if value]
    if len(present) == 3 and page.twitter_card:
        return result(O07, "pass", "Open Graph und Twitter-Card sind gesetzt.")
    if len(present) == 3:
        return result(O07, "warning", "Open Graph ist vollständig, die Twitter-Card fehlt.", (page.final_url,))
    if present:
        missing = ", ".join(name for name in ("Titel", "Beschreibung", "Bild") if name not in present)
        return result(O07, "warning", f"Bei Open Graph fehlt: {missing}.", (page.final_url,))
    return result(O07, "fail", "Open-Graph-Angaben fehlen.", (page.final_url,))


def check_keyword_use(page: PageSnapshot) -> CheckResult:
    """O10: no single content word dominates the visible text."""

    tokens = [token.casefold() for token in re.findall(r"\w+", page.text, flags=re.UNICODE) if len(token) >= 5]
    if len(tokens) < 40:
        return result(O10, "pass", "Der Text ist zu kurz für eine Häufung.")
    word, count = Counter(tokens).most_common(1)[0]
    share = count / len(tokens)
    if share > 0.15 and count >= 12:
        return result(O10, "fail", f"„{word}“ macht {round(share * 100)} % der längeren Wörter aus.", (page.final_url,))
    if share > 0.08 and count >= 8:
        return result(O10, "warning", f"„{word}“ kommt {count} Mal vor.", (page.final_url,))
    return result(O10, "pass", "Kein einzelnes Wort dominiert den Text.")
