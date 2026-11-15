"""Polite breadth-first crawl of one site."""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx
import structlog

from app.crawler.errors import UnsafeUrlError
from app.crawler.robots import RobotsPolicy
from app.crawler.safety import assert_public_url
from app.crawler.types import CrawledPage, CrawlOutput
from app.crawler.urls import crawl_key, is_skippable_path, same_site
from app.extractors.html_extract import extract_links, looks_like_html

MAX_BODY_BYTES = 2_000_000
logger = structlog.get_logger()


@dataclass(frozen=True)
class CrawlOptions:
    """Limits for a single audit crawl."""

    user_agent: str
    max_pages: int
    follow_links: bool
    delay_seconds: float


async def crawl_site(start_url: str, options: CrawlOptions) -> CrawlOutput:
    """Fetch the start URL and, when allowed, a bounded set of same-site HTML links.

    robots.txt is always requested first. A disallow of the start URL stops the crawl.
    An unreadable robots.txt limits the run to the URL the user submitted.
    """

    assert_public_url(start_url)
    parts = urlsplit(start_url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    timeout = httpx.Timeout(20.0, connect=10.0)
    headers = {
        "User-Agent": options.user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "de,en;q=0.8",
    }

    async def guard(request: httpx.Request) -> None:
        assert_public_url(str(request.url))

    async with httpx.AsyncClient(
        headers=headers,
        follow_redirects=True,
        timeout=timeout,
        max_redirects=5,
        event_hooks={"request": [guard]},
    ) as client:
        robots_status, robots_body = await _fetch_robots(client, robots_url)
        policy = RobotsPolicy(robots_body, robots_status)
        if not policy.allowed(options.user_agent, start_url):
            return CrawlOutput(
                pages=(),
                robots_txt=robots_body,
                robots_status=robots_status,
                blocked_by_robots=True,
            )

        delay = min(10.0, max(options.delay_seconds, policy.crawl_delay(options.user_agent)))
        follow_links = options.follow_links and not policy.unreadable
        queue: deque[str] = deque([start_url])
        seen = {crawl_key(start_url)}
        pages: list[CrawledPage] = []
        first = True
        while queue and len(pages) < options.max_pages:
            url = queue.popleft()
            if not policy.allowed(options.user_agent, url):
                continue
            if not first and delay > 0:
                await _sleep(delay)
            first = False
            crawled = await _fetch(client, url)
            pages.append(crawled)
            if not follow_links or crawled.error or not looks_like_html(crawled.content_type, crawled.body):
                continue
            for link in extract_links(crawled.body, crawled.content_type, crawled.final_url):
                if not same_site(link, start_url) or is_skippable_path(link):
                    continue
                key = crawl_key(link)
                if key in seen:
                    continue
                seen.add(key)
                queue.append(key)
        return CrawlOutput(
            pages=tuple(pages),
            robots_txt=robots_body,
            robots_status=robots_status,
            blocked_by_robots=False,
        )


async def _sleep(delay: float) -> None:
    await asyncio.sleep(delay)


async def _fetch_robots(client: httpx.AsyncClient, url: str) -> tuple[int | None, str | None]:
    try:
        page = await _fetch(client, url)
    except Exception:
        logger.warning("robots_fetch_failed", url=url)
        return None, None
    if page.error or page.status_code != 200:
        return page.status_code or None, None
    return page.status_code, page.body.decode("utf-8", errors="replace")


async def _fetch(client: httpx.AsyncClient, url: str) -> CrawledPage:
    try:
        async with client.stream("GET", url) as response:
            body = await _read_limited(response, MAX_BODY_BYTES)
            history = [str(item.url) for item in response.history]
            final_url = str(response.url)
            chain = history + [final_url]
            robots_values = response.headers.get_list("x-robots-tag")
            return CrawledPage(
                requested_url=url,
                final_url=final_url,
                status_code=response.status_code,
                redirect_count=len(response.history),
                redirect_loop=len(chain) != len({crawl_key(item) for item in chain}),
                content_type=response.headers.get("content-type", ""),
                header_robots=", ".join(robots_values) if robots_values else None,
                body=body,
            )
    except UnsafeUrlError:
        return _failed(url, "Eine Weiterleitung auf eine nicht öffentliche Adresse wurde blockiert.")
    except httpx.TooManyRedirects:
        return _failed(url, "Zu viele Weiterleitungen.", redirect_loop=True)
    except httpx.HTTPError:
        logger.warning("fetch_failed", url=url)
        return _failed(url, "Die Seite konnte nicht geladen werden.")


def _failed(url: str, message: str, *, redirect_loop: bool = False) -> CrawledPage:
    return CrawledPage(
        requested_url=url,
        final_url=url,
        status_code=0,
        redirect_count=0,
        redirect_loop=redirect_loop,
        content_type="",
        header_robots=None,
        body=b"",
        error=message,
    )


async def _read_limited(response: httpx.Response, limit: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    async for chunk in response.aiter_bytes():
        if size >= limit:
            break
        remaining = limit - size
        piece = chunk[:remaining]
        chunks.append(piece)
        size += len(piece)
        if len(chunk) > remaining:
            break
    return b"".join(chunks)
