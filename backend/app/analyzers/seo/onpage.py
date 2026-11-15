"""On-page checks O01–O03."""

from __future__ import annotations

from app.analyzers.common import Spec, result
from app.domain import CheckResult, CheckStatus, PageSnapshot

O01 = Spec(
    "O01",
    "high",
    "Title",
    "Einen eindeutigen Title mit etwa 50–60 Zeichen setzen, der das Thema der Seite nennt.",
    quick_win=True,
)
O02 = Spec(
    "O02",
    "medium",
    "Meta-Description",
    "Eine Meta-Description mit etwa 120–160 Zeichen ergänzen, die zum Weiterlesen einlädt.",
    quick_win=True,
)
O03 = Spec(
    "O03",
    "high",
    "H1",
    "Genau eine H1 setzen, die das Seitenthema in wenigen Worten nennt.",
    quick_win=True,
)


def check_title(page: PageSnapshot) -> CheckResult:
    """O01: a title exists and is close to 50–60 characters."""

    if not page.title:
        return result(O01, "fail", "Der Title fehlt.", (page.final_url,))
    length = len(page.title)
    status = _band(length, ideal=(50, 60), soft=(35, 70))
    if status == "pass":
        return result(O01, "pass", "Die Titles liegen im Bereich von 50–60 Zeichen.")
    text = f"Der Title hat {length} Zeichen. Ziel sind 50–60 Zeichen."
    return result(O01, status, text, (page.final_url,))


def check_meta_description(page: PageSnapshot) -> CheckResult:
    """O02: a meta description exists and is close to 120–160 characters."""

    if not page.meta_description:
        return result(O02, "fail", "Die Meta-Description fehlt.", (page.final_url,))
    length = len(page.meta_description)
    status = _band(length, ideal=(120, 160), soft=(70, 180))
    if status == "pass":
        return result(O02, "pass", "Die Meta-Descriptions liegen im Bereich von 120–160 Zeichen.")
    text = f"Die Meta-Description hat {length} Zeichen. Ziel sind 120–160 Zeichen."
    return result(O02, status, text, (page.final_url,))


def check_h1(page: PageSnapshot) -> CheckResult:
    """O03: exactly one H1, not overly long."""

    count = len(page.h1)
    if count == 0:
        return result(O03, "fail", "Die Seite hat keine H1.", (page.final_url,))
    if count > 1:
        return result(
            O03,
            "fail",
            f"Die Seite hat {count} H1-Überschriften. Es soll genau eine geben.",
            (page.final_url,),
        )
    length = len(page.h1[0])
    if length > 70:
        return result(
            O03,
            "warning",
            f"Die H1 hat {length} Zeichen und ist damit schwer zu erfassen.",
            (page.final_url,),
        )
    return result(O03, "pass", "Die Seiten haben genau eine klare H1.")


def _band(length: int, *, ideal: tuple[int, int], soft: tuple[int, int]) -> CheckStatus:
    if ideal[0] <= length <= ideal[1]:
        return "pass"
    if soft[0] <= length <= soft[1]:
        return "warning"
    return "fail"
