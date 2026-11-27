"""GEO content checks G05–G08, G10–G12, and the citability rollup G14.

G14 requires G05, G06, G07, and G08. It is omitted only when those checks did not run.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from urllib.parse import urlsplit

from app.analyzers.common import Spec, result
from app.domain import CheckResult, CheckStatus, PageSnapshot

G05 = Spec(
    "G05",
    "high",
    "Antwort zuerst",
    "Den ersten Absatz als direkte Antwort schreiben, mit etwa 40 Wörtern, bevor Details folgen.",
)
G06 = Spec(
    "G06",
    "high",
    "Zitierbare Abschnitte",
    (
        "Mindestens einen in sich geschlossenen Absatz mit 40–100 Wörtern formulieren, "
        "den eine AI-Antwort übernehmen kann."
    ),
)
G08 = Spec(
    "G08",
    "high",
    "Klare Entität",
    (
        "Den Marken- oder Organisationsnamen im Text mehrfach und gleichlautend nennen, "
        "passend zu Organization- oder WebSite-Schema."
    ),
)
G14 = Spec(
    "G14",
    "high",
    "Zitierbarkeit",
    (
        "Direkte Antwort, zitierbare Absätze und eine klare Marke zusammenbringen. "
        "Das ist die Grundlage, auf der AI-Systeme die Seite zitieren."
    ),
)

_ORG_TYPES = {"organization", "website", "localbusiness", "corporation", "brand"}


def check_answer_first(page: PageSnapshot) -> CheckResult:
    """G05: the first paragraph is long enough to be a direct answer."""

    if not page.paragraph_words:
        return result(
            G05,
            "fail",
            "Die Seite hat keinen Absatz, der eine direkte Antwort trägt.",
            (page.final_url,),
        )
    first = page.paragraph_words[0]
    if first >= 40:
        return result(G05, "pass", "Der erste Absatz ist lang genug für eine direkte Antwort.")
    text = f"Der erste Absatz hat nur {first} Wörter. Für eine direkte Antwort sind etwa 40 nötig."
    if first >= 20:
        return result(G05, "warning", text, (page.final_url,))
    return result(G05, "fail", text, (page.final_url,))


def check_extractable(page: PageSnapshot) -> CheckResult:
    """G06: at least one self-contained passage of 40–100 words."""

    if any(40 <= count <= 100 for count in page.paragraph_words):
        return result(G06, "pass", "Mindestens ein Absatz liegt im zitierbaren Bereich von 40–100 Wörtern.")
    if any(count >= 20 for count in page.paragraph_words):
        return result(
            G06,
            "warning",
            "Absätze sind vorhanden, keiner liegt bei 40–100 Wörtern.",
            (page.final_url,),
        )
    return result(
        G06,
        "fail",
        "Es gibt keinen in sich geschlossenen, zitierbaren Abschnitt.",
        (page.final_url,),
    )


def check_entity_clarity(page: PageSnapshot) -> CheckResult:
    """G08: a stable brand name appears in the visible text."""

    names: list[str] = []
    for block in page.json_ld:
        if not block.valid_json:
            continue
        typed = {item.lower() for item in block.types}
        if not typed or typed & _ORG_TYPES:
            names.extend(block.names)
    label = _host_label(page.final_url)
    if label:
        names.append(label)
    candidates = list(dict.fromkeys(name for name in names if len(name) >= 3))
    if not candidates:
        return result(G08, "warning", "Aus der Domain lässt sich kein Markenname ableiten.", (page.final_url,))
    best_name, best_count = max(
        ((name, _mentions(page.text, name)) for name in candidates),
        key=lambda item: item[1],
    )
    if best_count >= 2:
        return result(G08, "pass", "Der Markenname kommt im Text mehrfach und gleichlautend vor.")
    if best_count == 1:
        return result(G08, "warning", f"„{best_name}“ kommt nur einmal im Text vor.", (page.final_url,))
    return result(
        G08,
        "fail",
        "Weder der Name aus den strukturierten Daten noch die Domain kommen im Text vor.",
        (page.final_url,),
    )


G07 = Spec(
    "G07",
    "medium",
    "Belegte Zahlen",
    "Pro wichtiger Seite mindestens eine konkrete Zahl, ein Jahr oder einen Prozentwert nennen, den man prüfen kann.",
)


def check_statistics(page: PageSnapshot) -> CheckResult:
    """G07: the visible copy contains at least one verifiable figure."""

    numbers = re.findall(r"\d[\d.,]*", page.text)
    substantial = [item for item in numbers if len(re.sub(r"\D", "", item)) >= 2]
    if substantial:
        return result(G07, "pass", "Der Text enthält mindestens eine mehrstellige Zahl.")
    if numbers:
        return result(G07, "warning", "Es gibt nur einstellige Ziffern, keine belegbare Zahl.", (page.final_url,))
    return result(G07, "fail", "Im sichtbaren Text steht keine Zahl.", (page.final_url,))


G10 = Spec(
    "G10",
    "medium",
    "FAQ-Struktur",
    "Häufige Fragen als echte Frage-Antwort-Blöcke oder als FAQPage-Schema auszeichnen.",
)
G11 = Spec(
    "G11",
    "medium",
    "Aktualität",
    "Ein sichtbares oder maschinenlesbares Datum setzen und Inhalte erkennbar aktuell halten.",
)
G12 = Spec(
    "G12",
    "medium",
    "E-E-A-T-Signale",
    "Einen Autor oder eine verantwortliche Person nennen, nicht nur den Firmennamen.",
)


def check_faq(page: PageSnapshot) -> CheckResult:
    """G10: FAQ schema or at least two question headings."""

    types = {item.lower() for fact in page.json_ld for item in fact.types}
    if "faqpage" in types or page.question_count >= 2:
        return result(G10, "pass", "Die Seite hat eine erkennbare FAQ-Struktur.")
    if page.question_count == 1:
        return result(G10, "warning", "Es gibt nur eine Frage, keinen FAQ-Block.", (page.final_url,))
    return result(G10, "warning", "Weder FAQ-Schema noch Frage-Überschriften gefunden.", (page.final_url,))


def check_freshness(page: PageSnapshot) -> CheckResult:
    """G11: a date signal exists and is not several years old."""

    if not page.date_signals:
        return result(G11, "warning", "Es gibt kein erkennbares Datum.", (page.final_url,))
    years: list[int] = []
    for signal in page.date_signals:
        match = re.search(r"(?:19|20)\d{2}", signal)
        if match:
            years.append(int(match.group(0)))
    if not years:
        return result(G11, "warning", "Ein Datum ist gesetzt, das Jahr ist nicht lesbar.", (page.final_url,))
    newest = max(years)
    current = datetime.now(UTC).year
    if newest >= current - 2:
        return result(G11, "pass", f"Das neueste Datensignal liegt im Jahr {newest}.")
    if newest >= current - 5:
        return result(G11, "warning", f"Das neueste Datensignal ist von {newest}.", (page.final_url,))
    return result(G11, "fail", f"Das neueste Datensignal ist von {newest}.", (page.final_url,))


def check_experience(page: PageSnapshot) -> CheckResult:
    """G12: an author signal, beyond the organization name alone."""

    if page.has_author:
        return result(G12, "pass", "Ein Autor oder eine verantwortliche Person ist genannt.")
    types = {item.lower() for fact in page.json_ld for item in fact.types}
    if types & {"organization", "website", "localbusiness"}:
        return result(G12, "warning", "Die Organisation ist genannt, ein Autor fehlt.", (page.final_url,))
    return result(G12, "fail", "Weder Autor noch Organisation sind als Vertrauenssignal erkennbar.", (page.final_url,))


def check_citability(results: list[CheckResult]) -> CheckResult | None:
    """G14: roll up G05–G08. A missing G07 is incomplete, not a skipped check."""

    keys = ("G05", "G06", "G07", "G08")
    wanted = {item.check_id: item for item in results if item.check_id in keys}
    if not wanted:
        return None
    points = {"pass": 1.0, "warning": 0.5, "fail": 0.0}
    score = sum(points[wanted[key].status] if key in wanted else 0.0 for key in keys) / len(keys)
    weak = [key for key in keys if key not in wanted or wanted[key].status != "pass"]
    labels = {
        "G05": "die direkte Antwort",
        "G06": "zitierbare Absätze",
        "G07": "belegte Zahlen",
        "G08": "die Markenklarheit",
    }
    urls = tuple(dict.fromkeys(url for key in weak if key in wanted for url in wanted[key].affected_urls))
    if set(wanted) == set(keys) and score >= 0.75:
        return result(G14, "pass", "Antwort, zitierbare Absätze, Zahlen und Markenklarheit stützen die Zitierbarkeit.")
    listed = ", ".join(labels[key] for key in weak)
    status: CheckStatus = "warning" if score >= 0.4 else "fail"
    return result(G14, status, f"Die Zitierbarkeit ist unvollständig. Offen: {listed}.", urls)


def _host_label(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    return host.split(".", 1)[0]


def _mentions(text: str, name: str) -> int:
    return len(re.findall(rf"\b{re.escape(name)}\b", text, flags=re.IGNORECASE | re.UNICODE))
