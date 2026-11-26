"""PDF export from the HTML report via Playwright Chromium."""

from __future__ import annotations

from app.crawler.render import RenderUnavailableError


def render_audit_pdf(html: str) -> bytes:
    """Print the self-contained HTML report to A4 PDF bytes."""

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RenderUnavailableError("PDF-Export ist in dieser Installation nicht verfügbar.") from exc

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()

                def _inline_only(route: object) -> None:
                    target = str(getattr(getattr(route, "request", None), "url", ""))
                    if target.startswith(("data:", "blob:", "about:")):
                        route.continue_()  # type: ignore[attr-defined]
                        return
                    route.abort()  # type: ignore[attr-defined]

                # The report is self-contained. Do not let Chromium fetch a logo or stylesheet URL.
                page.route("**/*", _inline_only)
                page.set_content(html, wait_until="domcontentloaded")
                return page.pdf(
                    format="A4",
                    print_background=True,
                    margin={"top": "16mm", "right": "14mm", "bottom": "16mm", "left": "14mm"},
                )
            finally:
                browser.close()
    except RenderUnavailableError:
        raise
    except Exception as exc:
        raise RenderUnavailableError("PDF-Export ist in dieser Installation nicht verfügbar.") from exc
