"""T14 with probed link statuses."""

from app.analyzers.seo.technical import check_broken_links
from tests.test_checks import context, page


def test_probed_404_is_reported() -> None:
    home = page(links=("https://example.com/missing",))
    result = check_broken_links(context(pages=(home,), link_status={"https://example.com/missing": 404}))
    assert result is not None
    assert result.status == "fail"
    assert "missing" in result.affected_urls[0]


def test_without_probe_or_fetch_the_check_is_skipped() -> None:
    home = page(links=("https://example.com/never-fetched",))
    assert check_broken_links(context(pages=(home,), link_status={})) is None


def test_none_status_on_fetched_target_is_ignored() -> None:
    home = page(links=("https://example.com/soft",), status_code=200)
    soft = page(
        url="https://example.com/soft",
        final_url="https://example.com/soft",
        status_code=None,
        links=(),
    )
    result = check_broken_links(context(pages=(home, soft)))
    assert result is None or "soft" not in "".join(result.affected_urls)
