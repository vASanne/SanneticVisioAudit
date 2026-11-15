"""URL normalization for crawl deduplication and same-site links."""

from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

from app.crawler.errors import UnsafeUrlError

_SKIP_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".css",
    ".js",
    ".mjs",
    ".mp4",
    ".zip",
    ".gz",
    ".xml",
    ".json",
    ".woff",
    ".woff2",
    ".ttf",
}


def normalize_start_url(raw: str) -> str:
    """Turn user input into an absolute http(s) URL without a fragment."""

    value = raw.strip()
    if not value:
        raise UnsafeUrlError("Bitte eine URL angeben.")
    if re.search(r"\s", value):
        raise UnsafeUrlError("Die URL enthält Leerzeichen.")
    if "://" not in value:
        value = f"https://{value}"
    parts = urlsplit(value)
    if parts.scheme.lower() not in {"http", "https"}:
        raise UnsafeUrlError("Nur http- und https-URLs sind erlaubt.")
    if parts.username or parts.password:
        raise UnsafeUrlError("URLs mit Zugangsdaten sind nicht erlaubt.")
    if not parts.hostname:
        raise UnsafeUrlError("Der Hostname fehlt.")
    try:
        port = parts.port
    except ValueError as exc:
        raise UnsafeUrlError("Der Port ist ungültig.") from exc
    host = parts.hostname.lower().rstrip(".")
    netloc = f"[{host}]" if ":" in host else host
    if port:
        netloc = f"{netloc}:{port}"
    path = parts.path or "/"
    return urlunsplit((parts.scheme.lower(), netloc, path, parts.query, ""))


def crawl_key(url: str) -> str:
    """Identity used to avoid crawling the same path twice."""

    parts = urlsplit(url)
    host = (parts.hostname or "").lower().rstrip(".")
    port = ""
    try:
        if parts.port and not (
            (parts.scheme == "http" and parts.port == 80) or (parts.scheme == "https" and parts.port == 443)
        ):
            port = f":{parts.port}"
    except ValueError:
        port = ""
    netloc = f"[{host}]{port}" if ":" in host else f"{host}{port}"
    path = parts.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), netloc, path, "", ""))


def same_site(left: str, right: str) -> bool:
    """True when both URLs belong to the same host, ignoring a leading www."""

    return _site_root(left) != "" and _site_root(left) == _site_root(right)


def is_skippable_path(url: str) -> bool:
    """True for assets that are not HTML documents."""

    path = urlsplit(url).path.lower()
    return any(path.endswith(extension) for extension in _SKIP_EXTENSIONS)


def _site_root(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    if host.startswith("www."):
        return host[4:]
    return host
