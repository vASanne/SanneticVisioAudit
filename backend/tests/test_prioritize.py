"""Impact ranking for issues."""

from app.scoring.prioritize import issue_impact, page_importance


def test_homepage_outranks_deep_urls() -> None:
    assert page_importance("https://example.com/", start_url="https://example.com/") == 1.0
    assert page_importance("https://example.com/a/b/c", start_url="https://example.com/") < 0.6
    assert page_importance("https://other.example/", start_url="https://example.com/") < 0.5


def test_critical_homepage_issue_has_high_impact() -> None:
    score = issue_impact(
        severity="critical",
        status="fail",
        affected_urls=["https://example.com/"],
        start_url="https://example.com/",
        quick_win=True,
    )
    low = issue_impact(
        severity="low",
        status="warning",
        affected_urls=["https://example.com/blog/a/b"],
        start_url="https://example.com/",
    )
    assert score > low
    assert score >= 80
