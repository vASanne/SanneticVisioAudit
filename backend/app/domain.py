"""Shared contracts for crawl results, checks, and scores."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

AuditState = Literal["pending", "running", "completed", "failed"]
Severity = Literal["critical", "high", "medium", "low"]
CheckStatus = Literal["pass", "warning", "fail"]

SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
STATUS_RANK = {"fail": 0, "warning": 1, "pass": 2}


@dataclass(frozen=True)
class JsonLdFact:
    """One JSON-LD node after parsing."""

    valid_json: bool
    types: tuple[str, ...] = ()
    has_context: bool = False
    names: tuple[str, ...] = ()
    dates: tuple[str, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class PageSnapshot:
    """Normalized page facts used by deterministic checks."""

    url: str
    final_url: str
    status_code: int
    redirect_count: int = 0
    redirect_loop: bool = False
    content_type: str = "text/html"
    title: str | None = None
    meta_description: str | None = None
    meta_robots: str | None = None
    header_robots: str | None = None
    canonical: str | None = None
    canonical_count: int = 0
    h1: tuple[str, ...] = ()
    text: str = ""
    word_count: int = 0
    is_html: bool = True
    script_count: int = 0
    content_hash: str = ""
    links: tuple[str, ...] = ()
    error: str | None = None
    viewport: str | None = None
    insecure_resources: tuple[str, ...] = ()
    json_ld: tuple[JsonLdFact, ...] = ()
    paragraph_words: tuple[int, ...] = ()
    html_bytes: int = 0
    heading_levels: tuple[int, ...] = ()
    images_total: int = 0
    images_missing_alt: int = 0
    images_empty_alt: int = 0
    hreflang: tuple[str, ...] = ()
    hreflang_hrefs: tuple[str, ...] = ()
    og_title: str | None = None
    og_description: str | None = None
    og_image: str | None = None
    twitter_card: str | None = None
    has_author: bool = False
    date_signals: tuple[str, ...] = ()
    question_count: int = 0
    hsts: bool = False
    content_security_policy: bool = False
    content_type_options: bool = False
    rendered_word_count: int | None = None


@dataclass(frozen=True)
class PageSpeedFacts:
    """Lab or field Core Web Vitals for the start URL."""

    source: str
    lcp_ms: float | None = None
    inp_ms: float | None = None
    cls: float | None = None


@dataclass(frozen=True)
class SiteContext:
    """Everything a site-level check is allowed to see."""

    start_url: str
    user_agent: str
    robots_txt: str | None
    robots_status: int | None
    pages: tuple[PageSnapshot, ...] = ()
    blocked_by_robots: bool = False
    sitemap_status: int | None = None
    sitemap_count: int | None = None
    llms_status: int | None = None
    llms_words: int = 0
    ai_txt_status: int | None = None
    pagespeed: PageSpeedFacts | None = None
    pagespeed_error: str | None = None
    link_status: dict[str, int] = field(default_factory=dict)
    important_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class CheckResult:
    """One explainable check outcome."""

    check_id: str
    status: CheckStatus
    severity: Severity
    title: str
    description: str
    recommendation: str
    affected_urls: tuple[str, ...] = ()
    quick_win: bool = False


@dataclass(frozen=True)
class CategoryScore:
    """Weighted score for one report category."""

    category: str
    score: float | None
    details: dict[str, object] = field(default_factory=dict)
