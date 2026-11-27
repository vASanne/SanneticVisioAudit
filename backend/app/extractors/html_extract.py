"""HTML facts for the SEO and GEO checks."""

from __future__ import annotations

import hashlib
import json
import re
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from app.crawler.types import CrawledPage
from app.crawler.urls import document_key, is_skippable_path
from app.domain import JsonLdFact, PageSnapshot


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
    canonicals = _merged_canonicals(soup, page)
    h1 = tuple(text for node in soup.find_all("h1") if (text := _clean(node.get_text(" ", strip=True))))
    links = extract_links(page.body, page.content_type, page.final_url) if is_html else ()
    description = _meta(soup, "description")
    robots = _robots_meta(soup)
    canonical_count = len(canonicals)
    script_count = _script_count(soup)
    viewport = _viewport(soup)
    insecure_resources = _insecure_resources(soup, page.final_url)
    json_ld = _json_ld_facts(soup)
    paragraph_words = _paragraph_words(soup)
    heading_levels = tuple(
        int(node.name[1]) for node in soup.find_all(re.compile(r"^h[1-6]$")) if getattr(node, "name", None)
    )
    images_total, images_missing_alt, images_empty_alt = _images(soup)
    hreflang, hreflang_hrefs = _hreflang(soup)
    question_count = sum(1 for node in soup.find_all(["h2", "h3", "h4", "p"]) if "?" in node.get_text(" ", strip=True))
    for tag in soup(["script", "style", "template", "svg", "title"]):
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
        viewport=viewport,
        insecure_resources=insecure_resources,
        json_ld=json_ld,
        paragraph_words=paragraph_words,
        html_bytes=len(page.body),
        heading_levels=heading_levels,
        images_total=images_total,
        images_missing_alt=images_missing_alt,
        images_empty_alt=images_empty_alt,
        hreflang=hreflang,
        hreflang_hrefs=hreflang_hrefs,
        og_title=_meta_property(soup, "og:title"),
        og_description=_meta_property(soup, "og:description"),
        og_image=_meta_property(soup, "og:image"),
        twitter_card=_meta(soup, "twitter:card"),
        has_author=_has_author(soup, json_ld),
        date_signals=_date_signals(soup, json_ld),
        question_count=question_count,
        hsts=_header_present(page.response_headers, "strict-transport-security"),
        content_security_policy=_header_present(page.response_headers, "content-security-policy"),
        content_type_options=_header_equals(page.response_headers, "x-content-type-options", "nosniff"),
    )


def _merged_canonicals(soup: BeautifulSoup, page: CrawledPage) -> tuple[str, ...]:
    """HTML canonicals plus a header canonical, without counting the same target twice."""

    found = list(_canonical_hrefs(soup, page.final_url))
    found.extend(_header_canonicals(page.link_headers, page.final_url))
    unique: list[str] = []
    seen: set[str] = set()
    for href in found:
        key = document_key(href)
        if key in seen:
            continue
        seen.add(key)
        unique.append(href)
    return tuple(unique)


def _header_canonicals(headers: tuple[str, ...], base_url: str) -> tuple[str, ...]:
    hrefs: list[str] = []
    for header in headers:
        for link in _split_link_header(header):
            href, params = _link_target(link)
            if href is None or not _rel_is_canonical(params):
                continue
            absolute = _absolute_http_url(base_url, href)
            if absolute:
                hrefs.append(absolute)
    return tuple(hrefs)


def _split_link_header(header: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    quoted = False
    for char in header:
        if char == '"':
            quoted = not quoted
        if char == "," and not quoted:
            piece = "".join(current).strip()
            if piece:
                parts.append(piece)
            current = []
            continue
        current.append(char)
    piece = "".join(current).strip()
    if piece:
        parts.append(piece)
    return parts


def _link_target(link: str) -> tuple[str | None, str]:
    if not link.startswith("<"):
        return None, ""
    end = link.find(">")
    if end < 1:
        return None, ""
    return link[1:end].strip(), link[end + 1 :]


def _rel_is_canonical(params: str) -> bool:
    match = re.search(r"""(?i)(?:^|;)\s*rel\s*=\s*(?:"([^"]*)"|([^;]+))""", params)
    if match is None:
        return False
    raw = match.group(1) if match.group(1) is not None else match.group(2)
    return "canonical" in {token.strip().lower() for token in raw.split()}


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


def _robots_meta(soup: BeautifulSoup) -> str | None:
    values: list[str] = []
    for tag in soup.find_all("meta"):
        raw = tag.get("name")
        if not isinstance(raw, str) or not _is_robots_name(raw):
            continue
        content = tag.get("content")
        cleaned = _clean(content if isinstance(content, str) else None)
        if cleaned:
            values.append(cleaned)
    return ", ".join(values) or None


def _is_robots_name(name: str) -> bool:
    lowered = name.lower()
    return lowered == "robots" or (lowered.endswith("bot") and lowered != "robot")


def _meta(soup: BeautifulSoup, name: str) -> str | None:
    for tag in soup.find_all("meta"):
        raw = tag.get("name")
        if isinstance(raw, str) and raw.lower() == name:
            content = tag.get("content")
            return _clean(content if isinstance(content, str) else None)
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


def _viewport(soup: BeautifulSoup) -> str | None:
    for tag in soup.find_all("meta"):
        raw = tag.get("name")
        if isinstance(raw, str) and raw.lower() == "viewport":
            content = tag.get("content")
            return _clean(content if isinstance(content, str) else None)
    return None


_EMBEDDED = {"script", "img", "iframe", "source", "video", "audio", "embed", "object"}


def _insecure_resources(soup: BeautifulSoup, page_url: str) -> tuple[str, ...]:
    """HTTP subresources on an HTTPS page (mixed content)."""

    if urlsplit(page_url).scheme != "https":
        return ()
    found: list[str] = []
    for tag in soup.find_all(True):
        name = getattr(tag, "name", "")
        if name not in _EMBEDDED and not (name == "link" and _is_stylesheet(tag.get("rel"))):
            continue
        for attr in ("src", "href"):
            value = tag.get(attr)
            if not isinstance(value, str) or not value.strip().lower().startswith("http://"):
                continue
            absolute = _absolute_http_url(page_url, value)
            if absolute and absolute not in found:
                found.append(absolute)
    return tuple(found[:20])


def _is_stylesheet(value: object) -> bool:
    if isinstance(value, list):
        return any(str(item).lower() == "stylesheet" for item in value)
    if isinstance(value, str):
        return "stylesheet" in {part.lower() for part in value.split()}
    return False


def _paragraph_words(soup: BeautifulSoup) -> tuple[int, ...]:
    counts: list[int] = []
    for node in soup.find_all("p"):
        text = _clean(node.get_text(" ", strip=True))
        if not text:
            continue
        counts.append(len(re.findall(r"\w+", text, flags=re.UNICODE)))
    return tuple(counts)


def _json_ld_facts(soup: BeautifulSoup) -> tuple[JsonLdFact, ...]:
    facts: list[JsonLdFact] = []
    for tag in soup.find_all("script"):
        kind = tag.get("type")
        if not isinstance(kind, str) or kind.lower() != "application/ld+json":
            continue
        raw = tag.string if isinstance(tag.string, str) else tag.get_text()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            facts.append(JsonLdFact(False, error="Das JSON-LD ist kein gültiges JSON."))
            continue
        facts.extend(_facts_from_payload(payload))
    return tuple(facts)


def _facts_from_payload(payload: object) -> list[JsonLdFact]:
    if isinstance(payload, list):
        facts: list[JsonLdFact] = []
        for item in payload:
            facts.extend(_facts_from_payload(item))
        return facts
    if not isinstance(payload, dict):
        return [JsonLdFact(False, error="Das JSON-LD ist kein Objekt.")]
    graph = payload.get("@graph")
    if isinstance(graph, list):
        parent_context = "@context" in payload
        nodes = [_fact(item, parent_context) for item in graph if isinstance(item, dict)]
        return nodes or [_fact(payload, False)]
    return [_fact(payload, False)]


def _fact(node: dict[str, object], inherited_context: bool) -> JsonLdFact:
    return JsonLdFact(
        valid_json=True,
        types=_types(node.get("@type")),
        has_context=inherited_context or "@context" in node,
        names=_names(node.get("name")),
        dates=_dates(node),
    )


def _types(value: object) -> tuple[str, ...]:
    if isinstance(value, str) and value.strip():
        return (value.strip(),)
    if isinstance(value, list):
        return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
    return ()


def _dates(node: dict[str, object]) -> tuple[str, ...]:
    found: list[str] = []
    for key in ("datePublished", "dateModified", "dateCreated"):
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            found.append(value.strip())
    return tuple(found)


def _images(soup: BeautifulSoup) -> tuple[int, int, int]:
    total = missing = empty = 0
    for node in soup.find_all("img"):
        total += 1
        alt = node.get("alt")
        if alt is None:
            missing += 1
        elif not str(alt).strip():
            empty += 1
    return total, missing, empty


def _script_count(soup: BeautifulSoup) -> int:
    """Count scripts that can change the DOM. JSON-LD is data, not a renderer."""

    count = 0
    for node in soup.find_all("script"):
        kind = node.get("type")
        if isinstance(kind, str) and "json" in kind.casefold():
            continue
        count += 1
    return count


def _hreflang(soup: BeautifulSoup) -> tuple[tuple[str, ...], tuple[str, ...]]:
    codes: list[str] = []
    hrefs: list[str] = []
    for node in soup.find_all("link"):
        rel = node.get("rel")
        values = rel if isinstance(rel, list) else str(rel or "").split()
        if "alternate" not in {str(item).lower() for item in values}:
            continue
        code = node.get("hreflang")
        if isinstance(code, str) and code.strip():
            codes.append(code.strip())
            hrefs.append(_absolute_href(node.get("href")))
    return tuple(codes), tuple(hrefs)


def _absolute_href(href: object) -> str:
    if not isinstance(href, str):
        return ""
    value = href.strip()
    parts = urlsplit(value)
    if parts.scheme.lower() in {"http", "https"} and parts.netloc:
        return value
    return ""


def _meta_property(soup: BeautifulSoup, name: str) -> str | None:
    for tag in soup.find_all("meta"):
        raw = tag.get("property")
        if isinstance(raw, str) and raw.lower() == name:
            content = tag.get("content")
            return _clean(content if isinstance(content, str) else None)
    return None


def _has_author(soup: BeautifulSoup, facts: tuple[JsonLdFact, ...]) -> bool:
    if _meta(soup, "author"):
        return True
    for node in soup.find_all("link"):
        rel = node.get("rel")
        values = rel if isinstance(rel, list) else str(rel or "").split()
        if "author" in {str(item).lower() for item in values}:
            return True
    return any(item.lower() == "person" for fact in facts for item in fact.types)


def _date_signals(soup: BeautifulSoup, facts: tuple[JsonLdFact, ...]) -> tuple[str, ...]:
    found: list[str] = []
    for name in ("article:published_time", "article:modified_time"):
        value = _meta_property(soup, name)
        if value:
            found.append(value)
    for node in soup.find_all("time"):
        raw = node.get("datetime")
        if isinstance(raw, str) and raw.strip():
            found.append(raw.strip())
    found.extend(date for fact in facts for date in fact.dates)
    return tuple(dict.fromkeys(found))


def _header_present(headers: tuple[tuple[str, str], ...], name: str) -> bool:
    return any(key.lower() == name and bool(value.strip()) for key, value in headers)


def _header_equals(headers: tuple[tuple[str, str], ...], name: str, expected: str) -> bool:
    wanted = expected.casefold()
    return any(key.lower() == name and value.strip().casefold() == wanted for key, value in headers)


def _names(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        text = " ".join(value.split())
        return (text,) if text else ()
    if isinstance(value, list):
        names = [_names(item) for item in value]
        return tuple(part for group in names for part in group)
    return ()


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    text = " ".join(value.split())
    return text or None
