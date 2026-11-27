"""PageSpeed check T09. Omitted when no API key is configured."""

from __future__ import annotations

from app.analyzers.common import Spec, result
from app.domain import CheckResult, PageSpeedFacts, SiteContext

T09 = Spec(
    "T09",
    "high",
    "Core Web Vitals",
    (
        "LCP unter 2,5 Sekunden, INP unter 200 Millisekunden und CLS unter 0,1 bringen. "
        "Feld-Daten aus CrUX gehen vor, sonst zählt der Lab-Wert."
    ),
)

_LCP_GOOD = 2500
_LCP_POOR = 4000
_INP_GOOD = 200
_INP_POOR = 500
_CLS_GOOD = 0.1
_CLS_POOR = 0.25


def check_pagespeed(context: SiteContext) -> CheckResult | None:
    """T09: Core Web Vitals for the start URL, when PageSpeed returned data."""

    if context.pagespeed is None and not context.pagespeed_error:
        return None
    if context.pagespeed_error:
        return result(T09, "warning", context.pagespeed_error, (context.start_url,))
    facts = context.pagespeed
    if facts is None:
        return None
    poor, mid = _bands(facts)
    source = "Felddaten" if facts.source == "field" else "Labordaten"
    if poor:
        return result(T09, "fail", f"{source}: {', '.join(poor)} liegen im schlechten Bereich.", (context.start_url,))
    missing = [
        name for name, value in (("LCP", facts.lcp_ms), ("INP", facts.inp_ms), ("CLS", facts.cls)) if value is None
    ]
    if not mid and not missing:
        return result(T09, "pass", f"{source} für LCP, INP und CLS liegen im guten Bereich.")
    notes = _vital_notes(mid, missing)
    return result(T09, "warning", f"{source}: {'. '.join(notes)}.", (context.start_url,))


def _vital_notes(mid: list[str], missing: list[str]) -> list[str]:
    notes: list[str] = []
    if mid:
        verb = "braucht" if len(mid) == 1 else "brauchen"
        notes.append(f"{', '.join(mid)} {verb} Verbesserung")
    if missing:
        verb = "fehlt" if len(missing) == 1 else "fehlen"
        notes.append(f"{', '.join(missing)} {verb}")
    return notes


def _bands(facts: PageSpeedFacts) -> tuple[list[str], list[str]]:
    poor: list[str] = []
    mid: list[str] = []
    _place(poor, mid, "LCP", facts.lcp_ms, _LCP_GOOD, _LCP_POOR)
    _place(poor, mid, "INP", facts.inp_ms, _INP_GOOD, _INP_POOR)
    _place(poor, mid, "CLS", facts.cls, _CLS_GOOD, _CLS_POOR)
    return poor, mid


def _place(poor: list[str], mid: list[str], name: str, value: float | None, good: float, bad: float) -> None:
    if value is None:
        return
    if value > bad:
        poor.append(name)
    elif value > good:
        mid.append(name)
