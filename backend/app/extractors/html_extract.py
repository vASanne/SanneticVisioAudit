"""HTML facts for the SEO and GEO checks."""

from __future__ import annotations

import hashlib
import re
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from app.crawler.types import CrawledPage
from app.crawler.urls import is_skippable_path
from app.domain import PageSnapshot


def looks_like_html(content_type: str, body: bytes) -> bool:
    """True when the response is an HTML document rather than an asset."""

    lowered = content_type.lower()
    if "html" in lowered:
        return True
    if lowered and not lowered.startswith("text/") and "xhtml" not in lowered:
        return False
    sample = body.lstrip()[:300].lower()
    return sample.startswith((b"<!doctype html", b"<html")) or b"<head" in sample or b"<body" in sample


def extract_links(body: bytes, content_type: str, base_url: str) -> tuple[str, ...]:
    """Return absolute http(s) links discovered in an HTML document."""

    if not body or not looks_like_html(content_type, body):
        return ()
    soup = BeautifulSoup(_decode(body, content_type), "lxml")
    links: list[str] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href")
        if not isinstance(href, str):
            continue
        absolute = _absolute_http_url(base_url, href)
        if absolute is None or is_skippable_path(absolute) or absolute in seen:
            continue
        seen.add(absolute)
        links.append(absolute)
    return tuple(links)


def extract_page(page: CrawledPage) -> PageSnapshot:
    """Parse one fetch into the facts the checks consume."""

    html = _decode(page.body, page.content_type) if page.body else ""
    is_html = looks_like_html(page.content_type, page.body)
    soup = BeautifulSoup(html, "lxml") if html else BeautifulSoup("", "lxml")
    title = _clean(soup.title.string) if soup.title and soup.title.string else None
    canonicals = _canonical_hrefs(soup, page.final_url)
    h1 = tuple(
        text
        for node in soup.find_all("h1")
        if (text := _clean(node.get_text(" ", strip=True)))
    )
    links = extract_links(page.body, page.content_type, page.final_url) if is_html else ()
    description = _meta(soup, "description")
    robots = _meta(soup, "robots")
    canonical_count = len(_canonical_tags(soup))
    script_count = len(soup.find_all("script"))
    for tag in soup(["script", "style", "noscript", "template", "svg", "title"]):
        tag.decompose()
    text = " ".join(soup.get_text(" ", strip=True).split())
    words = re.findall(r"\w+", text, flags=re.UNICODE)
    return PageSnapshot(
        url=page.requested_url,
        final_url=page.final_url,
        status_code=page.status_code,
        redirect_count=page.redirect_count,
        redirect_loop=page.redirect_loop,
        content_type=page.content_type,
        title=title,
        meta_description=description,
        meta_robots=robots,
        header_robots=page.header_robots,
        canonical=canonicals[0] if canonicals else None,
        canonical_count=canonical_count,
        h1=h1,
        text=text,
        word_count=len(words),
        is_html=is_html,
        script_count=script_count,
        content_hash=hashlib.sha256(page.body).hexdigest() if page.body else "",
        links=links,
        error=page.error,
    )


def _canonical_tags(soup: BeautifulSoup) -> list[object]:
    return [tag for tag in soup.find_all("link") if _is_canonical(tag.get("rel"))]


def _canonical_hrefs(soup: BeautifulSoup, base_url: str) -> tuple[str, ...]:
    hrefs: list[str] = []
    for tag in _canonical_tags(soup):
        href = tag.get("href") if hasattr(tag, "get") else None
        if not isinstance(href, str):
            continue
        absolute = _absolute_http_url(base_url, href)
        if absolute:
            hrefs.append(absolute)
    return tuple(hrefs)


def _is_canonical(value: object) -> bool:
    if isinstance(value, list):
        return any(str(item).lower() == "canonical" for item in value)
    if isinstance(value, str):
        return "canonical" in {part.lower() for part in value.split()}
    return False


def _meta(soup: BeautifulSoup, name: str) -> str | None:
    for tag in soup.find_all("meta"):
        raw = tag.get("name")
        if isinstance(raw, str) and raw.lower() == name:
            return _clean(tag.get("content") if isinstance(tag.get("content"), str) else None)
    return None


def _absolute_http_url(base_url: str, href: str) -> str | None:
    raw = href.strip()
    if not raw or raw.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    absolute = urljoin(base_url, raw)
    parts = urlsplit(absolute)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return None
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", parts.query, ""))


def _decode(body: bytes, content_type: str) -> str:
    charset = "utf-8"
    lowered = content_type.lower()
    if "charset=" in lowered:
        charset = lowered.split("charset=", 1)[1].split(";", 1)[0].strip().strip('"')
    try:
        return body.decode(charset, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    text = " ".join(value.split())
    return text or None
