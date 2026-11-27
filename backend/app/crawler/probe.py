"""Probe internal links that the crawl itself did not fetch."""

from __future__ import annotations

import asyncio

import httpx

from app.crawler.errors import UnsafeUrlError
from app.crawler.robots import RobotsPolicy
from app.crawler.runner import _PinnedTransport, _read_limited
from app.crawler.safety import assert_public_url
from app.crawler.urls import crawl_key, same_site
from app.domain import PageSnapshot


async def probe_internal_links(
    pages: tuple[PageSnapshot, ...],
    *,
    user_agent: str,
    robots_txt: str | None,
    robots_status: int | None,
    delay_seconds: float,
    max_probes: int,
) -> dict[str, int]:
    """HEAD (then GET fallback) same-site links missing from the crawl.

    Returns crawl_key → status_code. Robots Disallow skips a URL.
    """

    if max_probes < 1 or not pages:
        return {}
    fetched = {crawl_key(page.final_url) for page in pages}
    policy = RobotsPolicy(robots_txt, robots_status)
    candidates: list[str] = []
    seen: set[str] = set()
    for page in pages:
        for link in page.links:
            if not same_site(page.final_url, link):
                continue
            key = crawl_key(link)
            if key in fetched or key in seen:
                continue
            seen.add(key)
            candidates.append(link)
            if len(candidates) >= max_probes:
                break
        if len(candidates) >= max_probes:
            break

    statuses: dict[str, int] = {}
    headers = {"User-Agent": user_agent, "Accept": "*/*"}

    async def guard(request: httpx.Request) -> None:
        assert_public_url(str(request.url))

    async with httpx.AsyncClient(
        transport=_PinnedTransport(),
        headers=headers,
        follow_redirects=True,
        max_redirects=5,
        timeout=httpx.Timeout(15.0),
        event_hooks={"request": [guard]},
    ) as client:
        for link in candidates:
            try:
                assert_public_url(link)
            except UnsafeUrlError:
                continue
            if not policy.allowed(user_agent, link):
                continue
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)
            status = await _status(client, link)
            if status is not None:
                statuses[crawl_key(link)] = status
    return statuses


async def _status(client: httpx.AsyncClient, url: str) -> int | None:
    try:
        response = await client.head(url)
        if response.status_code in {405, 501}:
            async with client.stream("GET", url) as streamed:
                await _read_limited(streamed, 4096)
                return int(streamed.status_code)
        return int(response.status_code)
    except UnsafeUrlError:
        return None
    except httpx.HTTPError:
        return 0
