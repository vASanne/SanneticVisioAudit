"""Optional Playwright rendering for pages whose raw HTML is thin."""

from __future__ import annotations

import re
from typing import NoReturn
from urllib.parse import urlsplit

from app.crawler.safety import assert_public_url


class RenderUnavailableError(RuntimeError):
    """Chromium is not installed in this runtime."""


_UNAVAILABLE = "JavaScript-Rendering ist in dieser Installation nicht verfügbar."


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


def _start_playwright() -> object:
    try:
        return _playwright_factory()().start()
    except Exception as exc:
        _raise_startup_failure(exc)


def _playwright_factory() -> object:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RenderUnavailableError(_UNAVAILABLE) from exc
    return sync_playwright


def _launch(playwright: object) -> object:
    try:
        chromium = getattr(playwright, "chromium")
        return chromium.launch(headless=True)
    except Exception as exc:
        _raise_startup_failure(exc)


def _count_pages(page: object, urls: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for url in urls:
        text = _visible_text(page, url)
        if text is None:
            continue
        counts[url] = len(re.findall(r"\w+", text, flags=re.UNICODE))
    return counts


def _install_request_guard(page: object) -> None:
    """Abort browser requests that are not public http(s) URLs, including redirects."""

    route = getattr(page, "route", None)
    if not callable(route):
        return

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
            except Exception:
                allowed = False
        if not allowed:
            if callable(abort):
                abort()
            return
        if callable(resume):
            resume()

    route("**/*", handler)


def _visible_text(page: object, url: str) -> str | None:
    try:
        goto = getattr(page, "goto")
        locator = getattr(page, "locator")
        goto(url, wait_until="domcontentloaded", timeout=20_000)
        text = locator("body").inner_text(timeout=5_000)
    except Exception as exc:
        if _must_propagate(exc):
            raise
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
