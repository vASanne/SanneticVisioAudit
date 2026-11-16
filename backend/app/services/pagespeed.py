"""PageSpeed Insights client and response parsing for T09."""

from __future__ import annotations

import httpx

from app.domain import PageSpeedFacts

_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


def fetch_pagespeed(url: str, api_key: str) -> tuple[PageSpeedFacts | None, str | None]:
    """Call PageSpeed. The error string is a customer-facing warning, not a traceback."""

    try:
        response = httpx.get(
            _ENDPOINT,
            params={"url": url, "strategy": "mobile", "category": "performance", "key": api_key},
            timeout=45,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        return None, "PageSpeed Insights war nicht erreichbar."
    if not isinstance(payload, dict):
        return None, "PageSpeed hat keine auswertbaren Vital-Werte geliefert."
    facts = parse_pagespeed(payload)
    if facts is None:
        return None, "PageSpeed hat keine auswertbaren Vital-Werte geliefert."
    return facts, None


def parse_pagespeed(payload: dict[str, object]) -> PageSpeedFacts | None:
    """Prefer CrUX field data and fall back to Lighthouse lab numbers."""

    experience = payload.get("loadingExperience")
    field = _field_metrics(experience if isinstance(experience, dict) else {})
    if field is not None:
        return field
    lighthouse = payload.get("lighthouseResult")
    return _lab_metrics(lighthouse if isinstance(lighthouse, dict) else {})


def _field_metrics(experience: dict[str, object]) -> PageSpeedFacts | None:
    metrics = experience.get("metrics")
    if not isinstance(metrics, dict):
        return None
    lcp = _percentile(metrics.get("LARGEST_CONTENTFUL_PAINT_MS"))
    inp = _percentile(metrics.get("INTERACTION_TO_NEXT_PAINT"))
    cls_raw = _percentile(metrics.get("CUMULATIVE_LAYOUT_SHIFT_SCORE"))
    cls = None if cls_raw is None else cls_raw / 100
    if lcp is None and inp is None and cls is None:
        return None
    return PageSpeedFacts("field", lcp, inp, cls)


def _lab_metrics(lighthouse: dict[str, object]) -> PageSpeedFacts | None:
    audits = lighthouse.get("audits")
    if not isinstance(audits, dict):
        return None
    lcp = _numeric(audits.get("largest-contentful-paint"))
    inp = _numeric(audits.get("interaction-to-next-paint"))
    cls = _numeric(audits.get("cumulative-layout-shift"))
    if lcp is None and inp is None and cls is None:
        return None
    return PageSpeedFacts("lab", lcp, inp, cls)


def _percentile(metric: object) -> float | None:
    if not isinstance(metric, dict):
        return None
    value = metric.get("percentile")
    if isinstance(value, int | float):
        return float(value)
    return None


def _numeric(audit: object) -> float | None:
    if not isinstance(audit, dict):
        return None
    value = audit.get("numericValue")
    if isinstance(value, int | float):
        return float(value)
    return None
