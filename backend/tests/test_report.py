"""Customer reports escape untrusted page content."""

from types import SimpleNamespace

from app.reports.html import render_audit_report


def test_report_escapes_markup_and_counts_passed_checks() -> None:
    issue = SimpleNamespace(
        severity="high",
        title="<script>alert(1)</script>",
        description="Offen",
        recommendation="Title setzen",
        affected_urls=("https://example.com/<tag>",),
        quick_win=True,
    )
    page = SimpleNamespace(status_code=200, title="Start", url="https://example.com/")
    html = render_audit_report(
        client_name="Kunde",
        url="https://example.com/",
        finished_at=None,
        pages_crawled=1,
        scores={"overall": 80.0, "seo": 75.0, "geo": 90.0, "technical": 70.0, "onpage": 80.0},
        overall_details={"checks": [{"status": "pass"}, {"status": "fail"}]},
        issues=[issue],
        pages=[page],
    )
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "1 von 2" in html
    assert "Schnell umsetzbar" in html
    assert "--color-primary" in html
    assert "Sannetic" in html


def test_white_label_logo_and_tokens() -> None:
    html = render_audit_report(
        client_name="Kunde",
        url="https://example.com/",
        finished_at=None,
        pages_crawled=1,
        scores={"overall": 80.0, "seo": 75.0, "geo": 90.0, "technical": 70.0, "onpage": 80.0},
        overall_details={"checks": []},
        issues=[],
        pages=[],
        logo_url="https://cdn.example/logo.svg",
        white_label=True,
        theme_tokens={"--color-primary": "#112233"},
        llm_summary="Kurzer Hinweis.",
        gsc_notes=["Search Console Hinweis"],
    )
    assert "cdn.example/logo.svg" in html
    assert "--color-primary:#112233" in html
    assert "Kurzer Hinweis." in html
    assert "Search Console Hinweis" in html
