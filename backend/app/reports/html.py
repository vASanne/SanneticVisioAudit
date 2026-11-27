"""Customer-facing HTML report."""

from __future__ import annotations

import base64
import hashlib
import html
import re
from collections.abc import Sequence
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from app.core.client_settings import css_declaration_is_safe
from app.crawler.safety import logo_reference_is_safe
from app.scoring.engine import METHODOLOGY

_ASSETS = Path(__file__).parent / "assets"
_STYLE_BLOCK = re.compile(r"<style>(.*?)</style>", re.DOTALL)
_ENV = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    autoescape=select_autoescape(enabled_extensions=("html",)),
)
_ENV.filters["http_url"] = lambda value: _http_url(value)
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
    issues: Sequence[object],
    pages: Sequence[object],
    logo_url: str | None = None,
    white_label: bool = False,
    theme_tokens: dict[str, str] | None = None,
    llm_summary: str | None = None,
    gsc_notes: list[str] | None = None,
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
        font_faces=_font_faces(),
        logo=_client_logo(logo_url if white_label else None),
        theme_overrides=_theme_overrides(theme_tokens if white_label else None),
        llm_summary=llm_summary,
        gsc_notes=gsc_notes or [],
    )


def report_branding(settings: dict[str, Any] | None, logo_url: str | None) -> dict[str, Any]:
    """Normalize client settings used by the HTML and PDF renderers."""

    data = settings or {}
    white_label = bool(data.get("white_label")) or bool(logo_url)
    raw_tokens = data.get("css_vars")
    tokens = raw_tokens if isinstance(raw_tokens, dict) else {}
    return {
        "white_label": white_label,
        "logo_url": logo_url,
        "theme_tokens": {str(key): str(value) for key, value in tokens.items()},
    }


@lru_cache(maxsize=1)
def _font_faces() -> Markup:
    inter = _font_data("inter-latin-wght-normal.woff2")
    mono = _font_data("jetbrains-mono-latin-wght-normal.woff2")
    css = (
        "@font-face{font-family:Inter;font-style:normal;font-weight:100 900;font-display:swap;"
        f"src:url(data:font/woff2;base64,{inter}) format('woff2');}}"
        "@font-face{font-family:'JetBrains Mono';font-style:normal;font-weight:100 800;font-display:swap;"
        f"src:url(data:font/woff2;base64,{mono}) format('woff2');}}"
    )
    # Font CSS is assembled from files shipped with this app, not from user input.
    return Markup(css)  # nosec B704  # noqa: S704


def _font_data(name: str) -> str:
    return base64.b64encode((_ASSETS / name).read_bytes()).decode("ascii")


def report_style_hash(document: str) -> str:
    """SHA-256 of the report style element text, base64, for a hash CSP source."""

    match = _STYLE_BLOCK.search(document)
    css = match.group(1) if match else ""
    digest = hashlib.sha256(css.encode("utf-8")).digest()
    return base64.b64encode(digest).decode("ascii")


def _client_logo(logo_url: str | None) -> Markup:
    if logo_url and logo_reference_is_safe(logo_url):
        safe = html.escape(logo_url, quote=True)
        # logo_url was escaped above and passed logo_reference_is_safe.
        return Markup(f'<img src="{safe}" alt="Logo" />')  # nosec B704  # noqa: S704
    return _logo()


@lru_cache(maxsize=1)
def _logo() -> Markup:
    raw = (_ASSETS / "lockup.svg").read_text(encoding="utf-8")
    raw = re.sub(r"<\?xml[^>]*\?>", "", raw).strip()
    # The lockup is a static asset in this repository.
    return Markup(raw)  # nosec B704  # noqa: S704


def _http_url(value: object) -> str:
    text = str(value or "").strip()
    parts = urlsplit(text)
    if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
        return ""
    return text


def _theme_overrides(tokens: dict[str, str] | None) -> Markup:
    if not tokens:
        return Markup("")
    lines: list[str] = []
    for key, value in tokens.items():
        if not css_declaration_is_safe(str(key), str(value)):
            continue
        lines.append(f"{html.escape(str(key))}:{html.escape(value.strip())};")
    if not lines:
        return Markup("")
    # Names and values passed css_declaration_is_safe and are HTML-escaped.
    return Markup(":root{" + "".join(lines) + "}")  # nosec B704  # noqa: S704


def _counts(details: dict[str, object]) -> tuple[int, int]:
    checks = details.get("checks")
    if not isinstance(checks, list):
        return 0, 0
    passed = sum(1 for item in checks if isinstance(item, dict) and item.get("status") == "pass")
    return passed, len(checks)


def _timestamp(value: datetime | None) -> str:
    if value is None:
        moment = datetime.now(UTC)
    elif value.tzinfo is None:
        moment = value.replace(tzinfo=UTC)
    else:
        moment = value.astimezone(UTC)
    return moment.strftime("%d.%m.%Y %H:%M UTC")
