"""Transparent weighted scores.

The score of a category is the share of severity weight that the checks earned:

    sum(weight(severity) * factor(status)) / sum(weight(severity)) * 100

Weights: critical 5, high 3, medium 2, low 1.
Factors: pass 1, warning 0.5, fail 0.
Checks that were not run are omitted. They are not counted as passed.
Results are rounded to one decimal place.
"""

from __future__ import annotations

from app.domain import CategoryScore, CheckResult, CheckStatus, Severity

SEVERITY_WEIGHTS: dict[Severity, int] = {"critical": 5, "high": 3, "medium": 2, "low": 1}
STATUS_FACTORS: dict[CheckStatus, float] = {"pass": 1.0, "warning": 0.5, "fail": 0.0}

METHODOLOGY = (
    "Jeder ausgeführte Check hat ein Gewicht nach Schweregrad: kritisch 5, hoch 3, mittel 2, niedrig 1. "
    "Bestanden zählt voll, ein Hinweis zur Hälfte, ein Fehlschlag gar nicht. "
    "Der Score ist dieser gewichtete Anteil, gerundet auf eine Nachkommastelle. "
    "Checks ohne auswertbare Seiten fließen nicht ein und gelten nicht als bestanden."
)

_GROUPS: dict[str, tuple[str, ...]] = {
    "technical": ("T",),
    "onpage": ("O",),
    "seo": ("T", "O"),
    "geo": ("G",),
    "overall": ("T", "O", "G", "X"),
}


def score_checks(results: list[CheckResult]) -> list[CategoryScore]:
    """Score technical, on-page, SEO, GEO, and the overall result."""

    scored: list[CategoryScore] = []
    for category, prefixes in _GROUPS.items():
        items = [item for item in results if item.check_id.startswith(prefixes)]
        value, details = _score(items)
        if value is None:
            continue
        scored.append(CategoryScore(category=category, score=value, details=details))
    return scored


def _score(items: list[CheckResult]) -> tuple[float | None, dict[str, object]]:
    if not items:
        return None, {}
    weight_total = 0
    earned = 0.0
    rows: list[dict[str, object]] = []
    for item in items:
        weight = SEVERITY_WEIGHTS[item.severity]
        factor = STATUS_FACTORS[item.status]
        points = weight * factor
        weight_total += weight
        earned += points
        rows.append(
            {
                "id": item.check_id,
                "status": item.status,
                "severity": item.severity,
                "weight": weight,
                "earned": points,
            }
        )
    score = round(earned / weight_total * 100, 1)
    return score, {
        "formula": "sum(weight * factor) / sum(weight) * 100",
        "weights": SEVERITY_WEIGHTS,
        "factors": STATUS_FACTORS,
        "checks": rows,
    }
