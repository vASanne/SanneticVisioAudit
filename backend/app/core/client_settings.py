"""Allow-list for client settings stored from the API.

Unknown keys are dropped. The Search Console access token is write-only and
is never copied into API responses.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit

_CSS_NAME = re.compile(r"^--[a-z0-9-]{1,40}$")
_CSS_VALUE = re.compile(r"^(#[0-9a-fA-F]{3,8}|[a-zA-Z]{3,40}|\d{1,4}(\.\d+)?(px|rem|em|%)?)$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PATH = re.compile(r"^/[\w.~%!$&'()*+,;=:@/-]{0,200}$")
_PUBLIC_KEYS = (
    "white_label",
    "css_vars",
    "important_paths",
    "gsc_site_url",
    "gsc_start_date",
    "gsc_end_date",
    "gsc_snapshot",
)


class SettingsRejected(ValueError):
    """The client settings payload is not in the allowed shape."""


def css_declaration_is_safe(name: str, value: str) -> bool:
    return bool(_CSS_NAME.match(name) and _CSS_VALUE.match(value.strip()))


def sanitize_client_settings(
    incoming: dict[str, Any] | None,
    *,
    existing: dict[str, Any] | None,
    is_admin: bool,
) -> dict[str, Any]:
    """Merge an update onto the stored settings and keep only known keys."""

    if incoming is None:
        incoming = {}
    if not isinstance(incoming, dict):
        raise SettingsRejected("settings must be an object")
    stored = dict(existing or {})
    cleaned: dict[str, Any] = {}
    cleaned["white_label"] = _bool_field(incoming, stored, "white_label")
    if "css_vars" in incoming:
        cleaned["css_vars"] = _css_vars(incoming.get("css_vars"))
    elif isinstance(stored.get("css_vars"), dict):
        cleaned["css_vars"] = _css_vars(stored.get("css_vars"))
    if "important_paths" in incoming:
        cleaned["important_paths"] = _paths(incoming.get("important_paths"))
    elif isinstance(stored.get("important_paths"), list):
        cleaned["important_paths"] = _paths(stored.get("important_paths"))
    if "gsc_site_url" in incoming:
        cleaned["gsc_site_url"] = _site_url(incoming.get("gsc_site_url"))
    elif isinstance(stored.get("gsc_site_url"), str):
        cleaned["gsc_site_url"] = _site_url(stored.get("gsc_site_url"))
    for key in ("gsc_start_date", "gsc_end_date"):
        if key in incoming:
            cleaned[key] = _date_field(incoming.get(key), key)
        elif isinstance(stored.get(key), str):
            cleaned[key] = _date_field(stored.get(key), key)
    if "gsc_snapshot" in incoming:
        snapshot = _snapshot(incoming.get("gsc_snapshot"))
        if snapshot is not None:
            cleaned["gsc_snapshot"] = snapshot
    elif isinstance(stored.get("gsc_snapshot"), dict):
        snapshot = _snapshot(stored.get("gsc_snapshot"))
        if snapshot is not None:
            cleaned["gsc_snapshot"] = snapshot
    token = _access_token(incoming, stored, is_admin=is_admin)
    if token:
        cleaned["gsc_access_token"] = token
    return {key: value for key, value in cleaned.items() if value is not None or key == "white_label"}


def public_client_settings(settings: dict[str, Any] | None) -> dict[str, Any]:
    """Settings safe to return from the API. Secrets are reduced to a flag."""

    data = dict(settings or {})
    configured = bool(str(data.get("gsc_access_token") or "").strip())
    visible = {key: data[key] for key in _PUBLIC_KEYS if key in data}
    if configured:
        visible["gsc_token_configured"] = True
    return visible


def _bool_field(incoming: dict[str, Any], stored: dict[str, Any], key: str) -> bool:
    if key in incoming:
        value = incoming[key]
        if not isinstance(value, bool):
            raise SettingsRejected(f"{key} must be a boolean")
        return value
    return bool(stored.get(key))


def _css_vars(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or len(value) > 40:
        raise SettingsRejected("css_vars is invalid")
    cleaned: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not isinstance(item, str):
            raise SettingsRejected("css_vars is invalid")
        if not css_declaration_is_safe(key, item):
            raise SettingsRejected("A CSS variable is not a plain color or length.")
        cleaned[key] = item.strip()
    return cleaned


def _paths(value: object) -> list[str]:
    if not isinstance(value, list) or len(value) > 30:
        raise SettingsRejected("important_paths is invalid")
    paths: list[str] = []
    for item in value:
        if not isinstance(item, str) or not _PATH.match(item) or item.startswith("//"):
            raise SettingsRejected("An important path must start with /.")
        paths.append(item)
    return paths


def _site_url(value: object) -> str | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str) or len(value) > 300:
        raise SettingsRejected("gsc_site_url is invalid")
    parts = urlsplit(value.strip())
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise SettingsRejected("gsc_site_url must be an https URL")
    return value.strip()


def _date_field(value: object, key: str) -> str | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str) or not _DATE.match(value):
        raise SettingsRejected(f"{key} must be YYYY-MM-DD")
    return value


def _snapshot(value: object) -> dict[str, list[dict[str, object]]] | None:
    if value in (None, {}):
        return None
    if not isinstance(value, dict):
        raise SettingsRejected("gsc_snapshot is invalid")
    rows = value.get("pages")
    if not isinstance(rows, list) or len(rows) > 25:
        raise SettingsRejected("gsc_snapshot is invalid")
    pages: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise SettingsRejected("gsc_snapshot is invalid")
        url = row.get("url")
        if not isinstance(url, str) or not url or len(url) > 2000:
            raise SettingsRejected("gsc_snapshot is invalid")
        pages.append(
            {
                "url": url,
                "clicks": _count(row.get("clicks")),
                "impressions": _count(row.get("impressions")),
            }
        )
    return {"pages": pages}


def _count(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return 0
    number = int(value)
    if number < 0:
        return 0
    return min(number, 1_000_000_000)


def _access_token(incoming: dict[str, Any], stored: dict[str, Any], *, is_admin: bool) -> str | None:
    if is_admin and "gsc_access_token" in incoming:
        value = incoming.get("gsc_access_token")
        if value in (None, ""):
            return None
        if not isinstance(value, str):
            raise SettingsRejected("gsc_access_token is invalid")
        token = value.strip()
        if not 8 <= len(token) <= 4096:
            raise SettingsRejected("gsc_access_token is invalid")
        return token
    existing = stored.get("gsc_access_token")
    if isinstance(existing, str) and existing.strip():
        return existing.strip()
    return None
