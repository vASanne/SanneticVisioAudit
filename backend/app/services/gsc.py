"""Google Search Console overlay for audits.

Deterministic scores stay unchanged. Notes only appear when credentials or a
stored snapshot exist on the client.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import get_settings
from app.domain import CheckResult, PageSnapshot


def notes_for_audit(
    client_settings: dict[str, Any],
    pages: tuple[PageSnapshot, ...],
    checks: list[CheckResult],
) -> list[str]:
    """Build German notes from a GSC snapshot or a live Search Analytics query."""

    snapshot = client_settings.get("gsc_snapshot")
    if isinstance(snapshot, dict) and snapshot:
        return _from_snapshot(snapshot, pages, checks)
    live = fetch_search_analytics(client_settings)
    if live:
        return _from_snapshot(live, pages, checks)
    return []


def fetch_search_analytics(client_settings: dict[str, Any]) -> dict[str, Any] | None:
    """Query Search Console when an OAuth access token and site URL are configured."""

    site = client_settings.get("gsc_site_url")
    token = client_settings.get("gsc_access_token") or get_settings().gsc_access_token
    if not isinstance(site, str) or not site.strip():
        return None
    if not isinstance(token, str) or not token.strip():
        return None
    endpoint = f"https://www.googleapis.com/webmasters/v3/sites/{quote(site, safe='')}/searchAnalytics/query"
    payload = {
        "startDate": str(client_settings.get("gsc_start_date") or "2025-01-01"),
        "endDate": str(client_settings.get("gsc_end_date") or "2026-12-31"),
        "dimensions": ["page"],
        "rowLimit": 25,
    }
    try:
        response = httpx.post(
            endpoint,
            headers={"Authorization": f"Bearer {token.strip()}", "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError):
        return None
    rows = data.get("rows") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return None
    pages: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        keys = row.get("keys")
        url = keys[0] if isinstance(keys, list) and keys else None
        if not isinstance(url, str):
            continue
        pages.append(
            {
                "url": url,
                "clicks": row.get("clicks", 0),
                "impressions": row.get("impressions", 0),
            }
        )
    return {"pages": pages}


def _from_snapshot(
    snapshot: dict[str, Any],
    pages: tuple[PageSnapshot, ...],
    checks: list[CheckResult],
) -> list[str]:
    rows = snapshot.get("pages")
    if not isinstance(rows, list) or not rows:
        return []
    crawled = {page.final_url for page in pages}
    failing = {url for item in checks if item.status == "fail" for url in item.affected_urls}
    notes: list[str] = []
    ranked = sorted(
        (row for row in rows if isinstance(row, dict) and isinstance(row.get("url"), str)),
        key=lambda row: float(row.get("impressions") or 0),
        reverse=True,
    )
    top = ranked[:5]
    if top:
        lead = top[0]
        notes.append(
            f"In der Search Console führt {lead['url']} mit "
            f"{int(lead.get('impressions') or 0)} Impressionen und {int(lead.get('clicks') or 0)} Klicks."
        )
    for row in top:
        url = str(row["url"])
        if url in failing:
            notes.append(f"Die URL mit Reichweite hat offene Fehler im Audit: {url}")
        elif url not in crawled:
            notes.append(f"Eine URL mit Reichweite wurde in diesem Crawl nicht gelesen: {url}")
    return notes[:6]
