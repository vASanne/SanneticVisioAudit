"""Customer-facing HTML report."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.scoring.engine import METHODOLOGY

_ENV = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    autoescape=select_autoescape(enabled_extensions=("html",)),
)
_LABELS = {
    "critical": "Kritisch",
    "high": "Hoch",
    "medium": "Mittel",
    "low": "Niedrig",
}


def render_audit_report(
    *,
    client_name: str,
    url: str,
    finished_at: datetime | None,
    pages_crawled: int,
    scores: dict[str, float | None],
    overall_details: dict[str, object] | None,
    issues: list[object],
    pages: list[object],
) -> str:
    """Render a self-contained HTML report for a completed audit."""

    passed, total = _counts(overall_details or {})
    template = _ENV.get_template("audit.html")
    return template.render(
        client_name=client_name,
        url=url,
        generated_label=_timestamp(finished_at),
        pages_crawled=pages_crawled,
        scores=scores,
        passed_count=passed,
        total_count=total,
        methodology=METHODOLOGY,
        issues=issues,
        pages=pages,
        labels=_LABELS,
    )


def _counts(details: dict[str, object]) -> tuple[int, int]:
    checks = details.get("checks")
    if not isinstance(checks, list):
        return 0, 0
    passed = sum(1 for item in checks if isinstance(item, dict) and item.get("status") == "pass")
    return passed, len(checks)


def _timestamp(value: datetime | None) -> str:
    if value is None:
        moment = datetime.now(timezone.utc)
    elif value.tzinfo is None:
        moment = value.replace(tzinfo=timezone.utc)
    else:
        moment = value.astimezone(timezone.utc)
    return moment.strftime("%d.%m.%Y %H:%M UTC")
