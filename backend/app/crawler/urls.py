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


_TRACKING_KEYS = {
    "dclid",
    "fbclid",
    "gclid",
    "gclsrc",
    "igshid",
    "mc_cid",
    "mc_eid",
    "msclkid",
    "twclid",
    "utm",
    "yclid",
    "_ga",
}


def crawl_key(url: str) -> str:
    """Identity used to avoid crawling the same document twice.

    A trailing slash is ignored. Tracking parameters are ignored. Any other
    query string stays, so ``/?p=123`` is a different page from ``/``.
    The result is not a fetch URL.
    """

    scheme, netloc, path, query = _parts(url)
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return urlunsplit((scheme, netloc, path, _content_query(query), ""))


def _content_query(query: str) -> str:
    if not query:
        return ""
    kept: list[str] = []
    for part in query.split("&"):
        if not part:
            continue
        key = part.split("=", 1)[0].lower()
        if key.startswith("utm_") or key in _TRACKING_KEYS:
            continue
        kept.append(part)
    kept.sort()
    return "&".join(kept)


def document_key(url: str) -> str:
    """Identity for redirects and canonicals. Query and trailing slash stay."""

    scheme, netloc, path, query = _parts(url)
    return urlunsplit((scheme, netloc, path, query, ""))


def repeats_document(urls: list[str]) -> bool:
    """True when two hops are the same document, not merely the same path."""

    seen: set[str] = set()
    for url in urls:
        key = document_key(url)
        if key in seen:
            return True
        seen.add(key)
    return False


def _parts(url: str) -> tuple[str, str, str, str]:
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
    return parts.scheme.lower(), netloc, parts.path or "/", parts.query


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
