"""Issue impact from severity, spread, and page importance."""

from __future__ import annotations

from urllib.parse import urlsplit

from app.crawler.urls import same_site
from app.domain import SEVERITY_RANK

_SEVERITY_POINTS = {"critical": 40, "high": 28, "medium": 16, "low": 8}
_STATUS_POINTS = {"fail": 20, "warning": 10, "pass": 0}


def page_importance(url: str, *, start_url: str, important_paths: list[str] | None = None) -> float:
    """0–1 importance. The start URL and configured paths rank highest."""

    path = urlsplit(url).path or "/"
    if crawl_same(url, start_url):
        return 1.0
    if same_site(url, start_url) and path in {"/", ""}:
        return 1.0
    if not same_site(url, start_url):
        return 0.2
    for item in important_paths or ():
        wanted = item if item.startswith("/") else f"/{item}"
        if path == wanted or path.rstrip("/") == wanted.rstrip("/"):
            return 0.9
    depth = len([part for part in path.split("/") if part])
    if depth <= 1:
        return 0.7
    if depth == 2:
        return 0.5
    return 0.3


def issue_impact(
    *,
    severity: str,
    status: str,
    affected_urls: list[str] | tuple[str, ...],
    start_url: str,
    important_paths: list[str] | None = None,
    quick_win: bool = False,
) -> float:
    """0–100 impact estimate for sorting. Higher means act sooner."""

    base = _SEVERITY_POINTS.get(severity, 8) + _STATUS_POINTS.get(status, 0)
    urls = list(affected_urls)
    spread = min(25.0, 5.0 * len(urls) if urls else 0.0)
    if not urls:
        importance = 0.5
    else:
        importance = max(page_importance(url, start_url=start_url, important_paths=important_paths) for url in urls)
    score = base + spread + 25.0 * importance
    if quick_win:
        score += 5.0
    return round(min(100.0, score), 1)


def crawl_same(left: str, right: str) -> bool:
    a = urlsplit(left)
    b = urlsplit(right)
    return (a.scheme, a.netloc.lower(), (a.path or "/").rstrip("/") or "/") == (
        b.scheme,
        b.netloc.lower(),
        (b.path or "/").rstrip("/") or "/",
    )


def sort_key(
    *,
    impact: float,
    severity: str,
    status: str,
    quick_win: bool,
    check_id: str,
) -> tuple[float, int, int, int, str]:
    """Sort by impact descending, then the usual ranks."""

    return (
        -impact,
        SEVERITY_RANK.get(severity, 9),
        0 if status == "fail" else 1 if status == "warning" else 2,
        0 if quick_win else 1,
        check_id,
    )
