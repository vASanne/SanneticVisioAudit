"""Optional Playwright rendering for pages whose raw HTML is thin."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import NoReturn, Protocol, cast
from urllib.parse import urlsplit

import structlog

from app.crawler.errors import UnsafeUrlError
from app.crawler.safety import assert_public_url

logger = structlog.get_logger()


class RenderUnavailableError(RuntimeError):
    """Chromium is not installed in this runtime."""


_UNAVAILABLE = "JavaScript-Rendering ist in dieser Installation nicht verfügbar."


class _Locator(Protocol):
    def inner_text(self, timeout: int) -> object: ...


class _Page(Protocol):
    def route(self, url: str, handler: Callable[[object], None]) -> None: ...

    def goto(self, url: str, *, wait_until: str, timeout: int) -> object: ...

    def locator(self, selector: str) -> _Locator: ...


class _Context(Protocol):
    def new_page(self) -> _Page: ...

    def close(self) -> None: ...


class _Browser(Protocol):
    def new_context(self, *, user_agent: str, accept_downloads: bool) -> _Context: ...

    def close(self) -> None: ...


class _BrowserType(Protocol):
    def launch(self, *, headless: bool) -> _Browser: ...


class _Playwright(Protocol):
    chromium: _BrowserType

    def stop(self) -> None: ...


class _PlaywrightStarter(Protocol):
    def start(self) -> _Playwright: ...


def rendered_word_counts(urls: list[str], user_agent: str) -> dict[str, int]:
    """Return visible body words after JavaScript, keyed by the requested URL.

    Only the caller decides which URLs are worth a browser. A timeout on one
    URL is skipped. A missing Playwright install raises RenderUnavailableError.
    """

    if not urls:
        return {}
    playwright = _start_playwright()
    try:
        browser = _launch(playwright)
        try:
            context = browser.new_context(user_agent=user_agent, accept_downloads=False)
            try:
                page = context.new_page()
                _install_request_guard(page)
                return _count_pages(page, urls)
            finally:
                context.close()
        finally:
            browser.close()
    finally:
        playwright.stop()


def _start_playwright() -> _Playwright:
    try:
        return _playwright_factory()().start()
    except Exception as exc:
        if _must_propagate(exc):
            raise
        # Driver and browser failures are a wide set. Log the type, then hide the message.
        logger.exception("playwright_start_failed")
        _raise_startup_failure(exc)


def _playwright_factory() -> Callable[[], _PlaywrightStarter]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RenderUnavailableError(_UNAVAILABLE) from exc
    return cast(Callable[[], _PlaywrightStarter], sync_playwright)


def _launch(playwright: _Playwright) -> _Browser:
    try:
        return playwright.chromium.launch(headless=True)
    except Exception as exc:
        if _must_propagate(exc):
            raise
        logger.exception("playwright_launch_failed")
        _raise_startup_failure(exc)


def _count_pages(page: _Page, urls: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for url in urls:
        text = _visible_text(page, url)
        if text is None:
            continue
        counts[url] = len(re.findall(r"\w+", text, flags=re.UNICODE))
    return counts


def _install_request_guard(page: _Page) -> None:
    """Abort browser requests that are not public http(s) URLs, including redirects."""

    def handler(route_obj: object) -> None:
        request = getattr(route_obj, "request", None)
        target = str(getattr(request, "url", ""))
        abort = getattr(route_obj, "abort", None)
        resume = getattr(route_obj, "continue_", None)
        allowed = target.startswith(("data:", "blob:", "about:"))
        if not allowed:
            try:
                parts = urlsplit(target)
                allowed = parts.scheme in {"http", "https"}
                if allowed:
                    assert_public_url(target)
            except (UnsafeUrlError, ValueError):
                allowed = False
        if not allowed:
            if callable(abort):
                abort()
            return
        if callable(resume):
            resume()

    page.route("**/*", handler)


def _visible_text(page: _Page, url: str) -> str | None:
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20_000)
        text = page.locator("body").inner_text(timeout=5_000)
    except Exception as exc:
        if _must_propagate(exc):
            raise
        logger.exception("render_text_failed")
        return None
    if not isinstance(text, str):
        return None
    return text


def _raise_startup_failure(exc: Exception) -> NoReturn:
    """Missing Chromium must stay a RenderUnavailableError, not a generic failure."""

    if _must_propagate(exc):
        raise exc
    raise RenderUnavailableError(_UNAVAILABLE) from exc


def _must_propagate(exc: Exception) -> bool:
    if isinstance(exc, RenderUnavailableError):
        return True
    return type(exc).__name__ == "SoftTimeLimitExceeded"
