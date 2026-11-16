"""Check behaviour for the MVP set."""

from app.analyzers.engine import aggregate, run_checks
from app.domain import CheckResult, JsonLdFact, PageSnapshot, SiteContext

UA = "SanneticVisionBot/1.0 (+https://sannetic.com/bot)"
START = "https://example.com/"


def page(**overrides: object) -> PageSnapshot:
    data: dict[str, object] = {
        "url": START,
        "final_url": START,
        "status_code": 200,
        "is_html": True,
        "title": "S" * 55,
        "meta_description": "D" * 140,
        "canonical": START,
        "canonical_count": 1,
        "h1": ("Leistung",),
        "word_count": 320,
        "text": "Example erklärt Example seit 2018 verständlich.",
        "viewport": "width=device-width, initial-scale=1",
        "paragraph_words": (48, 55),
        "heading_levels": (1, 2),
        "og_title": "Leistung",
        "og_description": "Beschreibung der Leistung",
        "og_image": "https://example.com/bild.jpg",
        "twitter_card": "summary_large_image",
        "has_author": True,
        "date_signals": ("2026-01-15",),
        "question_count": 2,
        "hsts": True,
        "content_security_policy": True,
        "content_type_options": True,
        "links": (START,),
        "json_ld": (
            JsonLdFact(True, ("Organization",), True, ("Example",)),
            JsonLdFact(True, ("WebSite",), True, ("Example",)),
        ),
    }
    data.update(overrides)
    return PageSnapshot(**data)  # type: ignore[arg-type]


def context(**overrides: object) -> SiteContext:
    data: dict[str, object] = {
        "start_url": START,
        "user_agent": UA,
        "robots_txt": (
            "User-agent: *\nDisallow:\n\n"
            "User-agent: GPTBot\nDisallow: /\n\n"
            "Sitemap: https://example.com/sitemap.xml\n"
        ),
        "robots_status": 200,
        "sitemap_status": 200,
        "sitemap_count": 4,
        "llms_status": 200,
        "llms_words": 60,
        "ai_txt_status": 404,
        "pages": (page(),),
    }
    data.update(overrides)
    return SiteContext(**data)  # type: ignore[arg-type]


def by_id(ctx: SiteContext) -> dict[str, CheckResult]:
    return {item.check_id: item for item in run_checks(ctx)}


def test_healthy_page_passes_the_mvp_checks() -> None:
    results = by_id(context())
    assert results["T01"].status == "pass"
    assert results["T02"].status == "pass"
    assert results["T03"].status == "pass"
    assert results["T04"].status == "pass"
    assert results["T05"].status == "pass"
    assert results["O01"].status == "pass"
    assert results["O02"].status == "pass"
    assert results["O03"].status == "pass"
    assert results["G01"].status == "pass"
    assert results["G04"].status == "pass"
    for check_id in (
        "T06",
        "T07",
        "T08",
        "T10",
        "T11",
        "T13",
        "T14",
        "T15",
        "O04",
        "O05",
        "O06",
        "O07",
        "O08",
        "O09",
        "O10",
        "G02",
        "G03",
        "G05",
        "G06",
        "G07",
        "G08",
        "G09",
        "G10",
        "G11",
        "G12",
        "G13",
        "G14",
        "X01",
        "X02",
        "X03",
        "X04",
    ):
        assert results[check_id].status == "pass", check_id
    assert "T09" not in results
    assert "T12" not in results


def test_http_error_fails_only_the_broken_url() -> None:
    broken = page(url="https://example.com/missing", final_url="https://example.com/missing", status_code=404, is_html=False)
    results = by_id(context(pages=(page(), broken)))
    assert results["T01"].status == "fail"
    assert results["T01"].affected_urls == ("https://example.com/missing",)
    assert results["O01"].status == "pass"


def test_redirect_chain_and_loop() -> None:
    assert by_id(context(pages=(page(redirect_count=1),)))["T02"].status == "pass"
    chained = by_id(context(pages=(page(redirect_count=2),)))["T02"]
    assert chained.status == "fail"
    looped = by_id(context(pages=(page(redirect_loop=True, redirect_count=3),)))["T02"]
    assert looped.status == "fail"
    assert "Kreis" in looped.description


def test_canonical_missing_multiple_and_foreign() -> None:
    assert by_id(context(pages=(page(canonical=None, canonical_count=0),)))["T03"].status == "warning"
    assert by_id(context(pages=(page(canonical_count=2),)))["T03"].status == "fail"
    foreign = by_id(context(pages=(page(canonical="https://example.com/andere"),)))["T03"]
    assert foreign.status == "warning"
    assert "andere" in foreign.description
    query = by_id(context(pages=(page(canonical="https://example.com/?ref=1"),)))["T03"]
    assert query.status == "warning"
    slash = by_id(
        context(
            pages=(
                page(
                    url="https://example.com/pfad",
                    final_url="https://example.com/pfad",
                    canonical="https://example.com/pfad/",
                ),
            )
        )
    )["T03"]
    assert slash.status == "warning"
    assert by_id(context(pages=(page(canonical="https://EXAMPLE.com/"),)))["T03"].status == "pass"


def test_noindex_in_meta_or_header() -> None:
    assert by_id(context(pages=(page(meta_robots="noindex, nofollow"),)))["T04"].status == "fail"
    assert by_id(context(pages=(page(header_robots="none"),)))["T04"].status == "fail"
    assert by_id(context(pages=(page(header_robots="googlebot: noindex"),)))["T04"].status == "fail"
    assert by_id(context(pages=(page(meta_robots="index, follow"),)))["T04"].status == "pass"


def test_robots_txt_missing_sitemap_and_disallow() -> None:
    missing = by_id(context(robots_txt=None, robots_status=404, pages=()))
    assert missing["T05"].status == "fail"
    assert missing["G01"].status == "pass"
    sitemap = by_id(context(robots_txt="User-agent: *\nDisallow:\n"))
    assert sitemap["T05"].status == "warning"
    blocked = "User-agent: *\nDisallow: /\n"
    denied = by_id(context(robots_txt=blocked, robots_status=200, blocked_by_robots=True, pages=()))
    assert denied["T01"].status == "fail"
    assert denied["T05"].status == "fail"
    assert denied["G01"].status == "fail"


def test_specific_allow_keeps_the_start_url_crawlable() -> None:
    robots = "User-agent: *\nDisallow: /\nAllow: /blog\n\nSitemap: https://example.com/sitemap.xml\n"
    start = "https://example.com/blog"
    results = by_id(context(start_url=start, robots_txt=robots, pages=(page(url=start, final_url=start),)))
    assert results["T05"].status == "pass"
    assert results["G01"].status == "pass"


def test_ai_bot_can_be_blocked_separately() -> None:
    robots = (
        "User-agent: *\nDisallow:\n\n"
        "User-agent: PerplexityBot\nDisallow: /\n\n"
        "Sitemap: https://example.com/sitemap.xml\n"
    )
    results = by_id(context(robots_txt=robots))
    assert results["T05"].status == "pass"
    assert results["G01"].status == "fail"
    assert "PerplexityBot" in results["G01"].description


def test_title_description_and_h1_bands() -> None:
    assert by_id(context(pages=(page(title=None),)))["O01"].status == "fail"
    assert by_id(context(pages=(page(title="T" * 40),)))["O01"].status == "warning"
    assert by_id(context(pages=(page(title="T" * 10),)))["O01"].status == "fail"
    assert by_id(context(pages=(page(meta_description=None),)))["O02"].status == "fail"
    assert by_id(context(pages=(page(meta_description="D" * 90),)))["O02"].status == "warning"
    assert by_id(context(pages=(page(h1=()),)))["O03"].status == "fail"
    assert by_id(context(pages=(page(h1=("Eins", "Zwei")),)))["O03"].status == "fail"
    assert by_id(context(pages=(page(h1=("H" * 80,)),)))["O03"].status == "warning"


def test_thin_html_fails_geo_content() -> None:
    thin = by_id(context(pages=(page(word_count=10, script_count=8),)))["G04"]
    assert thin.status == "fail"
    assert "JavaScript" in thin.recommendation
    assert by_id(context(pages=(page(word_count=50),)))["G04"].status == "warning"


def test_https_viewport_and_javascript() -> None:
    http = by_id(context(pages=(page(final_url="http://example.com/"),)))
    assert http["T07"].status == "fail"
    mixed = page(insecure_resources=("http://cdn.example.com/app.js",))
    assert by_id(context(pages=(mixed,)))["T07"].status == "fail"
    assert by_id(context(pages=(page(viewport=None),)))["T08"].status == "fail"
    assert by_id(context(pages=(page(viewport="width=1024"),)))["T08"].status == "warning"
    thin_js = by_id(context(pages=(page(word_count=12, script_count=6),)))["T11"]
    assert thin_js.status == "fail"


def test_schema_answer_and_citability() -> None:
    bare = page(json_ld=(), paragraph_words=(), text="Kein Markenname hier.")
    results = by_id(context(pages=(bare,)))
    assert results["O08"].status == "fail"
    assert "O09" not in results
    assert results["G05"].status == "fail"
    assert results["G09"].status == "fail"
    assert results["G14"].status == "fail"
    broken_json = page(json_ld=(JsonLdFact(False, error="Das JSON-LD ist kein gültiges JSON."),))
    assert by_id(context(pages=(broken_json,)))["O09"].status == "fail"
    article_only = page(json_ld=(JsonLdFact(True, ("Article",), True, ("Beitrag",)),))
    assert by_id(context(pages=(article_only,)))["G09"].status == "warning"


def test_broken_internal_link_and_indexability() -> None:
    start = page(links=("https://example.com/missing",))
    missing = page(
        url="https://example.com/missing",
        final_url="https://example.com/missing",
        status_code=404,
        is_html=False,
    )
    results = by_id(context(pages=(start, missing)))
    assert results["T14"].status == "fail"
    assert results["T14"].affected_urls == ("https://example.com/missing",)
    assert results["X01"].status == "fail"
    foreign = by_id(context(pages=(page(canonical="https://example.com/andere"),)))
    assert foreign["X01"].status == "warning"


def test_aggregate_counts_affected_pages() -> None:
    first = CheckResult("T01", "fail", "critical", "HTTP-Status", "HTTP 404.", "Fix", ("https://example.com/a",))
    second = CheckResult("T01", "pass", "critical", "HTTP-Status", "Alle geprüften Seiten antworten mit einem erfolgreichen HTTP-Status.", "Fix")
    third = CheckResult("T01", "fail", "critical", "HTTP-Status", "HTTP 500.", "Fix", ("https://example.com/c",))
    combined = aggregate([first, second, third])
    assert combined.status == "fail"
    assert combined.affected_urls == ("https://example.com/a", "https://example.com/c")
    assert combined.description.startswith("2 von 3 Seiten.")
