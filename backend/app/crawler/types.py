"""Fetched documents before HTML extraction."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CrawledPage:
    """One HTTP fetch, including a failure that never produced a body."""

    requested_url: str
    final_url: str
    status_code: int
    redirect_count: int
    redirect_loop: bool
    content_type: str
    header_robots: str | None
    body: bytes
    link_headers: tuple[str, ...] = ()
    response_headers: tuple[tuple[str, str], ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class CrawlOutput:
    """Pages plus the robots.txt response that governed the crawl."""

    pages: tuple[CrawledPage, ...]
    robots_txt: str | None
    robots_status: int | None
    blocked_by_robots: bool
    sitemap_status: int | None = None
    sitemap_count: int | None = None
    llms_status: int | None = None
    llms_words: int = 0
    ai_txt_status: int | None = None
