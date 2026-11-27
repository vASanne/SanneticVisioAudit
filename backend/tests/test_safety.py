"""The crawler only accepts public web URLs."""

import socket

import pytest
from app.crawler.errors import UnsafeUrlError
from app.crawler.robots import RobotsPolicy
from app.crawler.safety import assert_public_url, public_connect_host
from app.crawler.urls import crawl_key, document_key, normalize_start_url, repeats_document, same_site


def _public(host: str, _port: object, *_args: object, **_kwargs: object) -> list[tuple[object, ...]]:
    if host != "example.com":
        raise socket.gaierror(host)
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]


def _private(_host: str, _port: object, *_args: object, **_kwargs: object) -> list[tuple[object, ...]]:
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.1.1.1", 0))]


def _unused(*_args: object, **_kwargs: object) -> list[tuple[object, ...]]:
    raise AssertionError("DNS must not be queried for this URL")


def test_normalize_adds_https_and_drops_the_fragment() -> None:
    assert normalize_start_url("example.com/pfad#abschnitt") == "https://example.com/pfad"


def test_normalize_rejects_credentials_and_non_http() -> None:
    with pytest.raises(UnsafeUrlError):
        normalize_start_url("https://user:secret@example.com/")
    with pytest.raises(UnsafeUrlError):
        normalize_start_url("javascript:alert(1)")


def test_public_host_is_allowed() -> None:
    assert_public_url("https://example.com/audit", resolver=_public)


def _mixed(host: str, _port: object, *_args: object, **_kwargs: object) -> list[tuple[object, ...]]:
    if host != "example.com":
        raise socket.gaierror(host)
    return [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.1.1.1", 0)),
    ]


def test_private_and_local_targets_are_rejected() -> None:
    with pytest.raises(UnsafeUrlError):
        assert_public_url("http://127.0.0.1/", resolver=_unused)
    with pytest.raises(UnsafeUrlError):
        assert_public_url("http://169.254.169.254/", resolver=_unused)
    with pytest.raises(UnsafeUrlError):
        assert_public_url("http://localhost/admin", resolver=_unused)
    with pytest.raises(UnsafeUrlError):
        assert_public_url("https://example.com/", resolver=_private)
    with pytest.raises(UnsafeUrlError):
        assert_public_url("https://example.com/", resolver=_mixed)
    with pytest.raises(UnsafeUrlError):
        assert_public_url("http://[::1]/", resolver=_unused)
    with pytest.raises(UnsafeUrlError):
        assert_public_url("http://[::ffff:169.254.169.254]/", resolver=_unused)
    with pytest.raises(UnsafeUrlError):
        assert_public_url("http://2130706433/", resolver=_unused)
    with pytest.raises(UnsafeUrlError):
        assert_public_url("http://0177.0.0.1/", resolver=_unused)
    with pytest.raises(UnsafeUrlError):
        assert_public_url("http://127.1/", resolver=_unused)
    with pytest.raises(UnsafeUrlError):
        assert_public_url("http://metadata.google.internal/", resolver=_unused)
    with pytest.raises(UnsafeUrlError):
        assert_public_url("http://user:pass@example.com/", resolver=_unused)
    with pytest.raises(UnsafeUrlError):
        assert_public_url("file:///etc/passwd", resolver=_unused)
    with pytest.raises(UnsafeUrlError):
        public_connect_host("224.0.0.1", resolver=_unused)


def test_same_site_ignores_www_and_crawl_key_keeps_content_queries() -> None:
    assert same_site("https://www.example.com/a", "https://example.com/b")
    assert not same_site("https://example.com/", "https://other.example/")
    assert crawl_key("https://example.com/pfad/?utm=1") == crawl_key("https://example.com/pfad")
    assert crawl_key("https://example.com/?p=123") != crawl_key("https://example.com/")
    assert crawl_key("https://example.com/?b=2&a=1") == crawl_key("https://example.com/?a=1&b=2")


def test_connect_host_is_the_checked_public_address() -> None:
    assert public_connect_host("example.com", resolver=_public) == "93.184.216.34"
    with pytest.raises(UnsafeUrlError):
        public_connect_host("example.com", resolver=_private)
    with pytest.raises(UnsafeUrlError):
        public_connect_host("10.1.1.1", resolver=_unused)


def test_document_key_keeps_query_and_slash_and_detects_real_loops() -> None:
    assert document_key("https://EXAMPLE.com/pfad/?utm=1") != document_key("https://example.com/pfad")
    assert document_key("https://example.com/pfad/") != document_key("https://example.com/pfad")
    assert not repeats_document(["https://example.com/about/", "https://example.com/about"])
    assert repeats_document(["https://example.com/a", "https://example.com/b", "https://example.com/a"])


def test_longer_allow_beats_an_earlier_disallow() -> None:
    policy = RobotsPolicy("User-agent: *\nDisallow: /\nAllow: /blog\n", 200)
    assert policy.allowed("SanneticVisionBot/1.0", "https://example.com/blog")
    assert not policy.allowed("SanneticVisionBot/1.0", "https://example.com/other")
    wildcard = RobotsPolicy("User-agent: *\nDisallow: /*.pdf$\n", 200)
    assert not wildcard.allowed("*", "https://example.com/files/a.pdf")
    assert wildcard.allowed("*", "https://example.com/files/a.pdf.html")
    tie = RobotsPolicy("User-agent: OAI-SearchBot\nDisallow: /\nAllow: /\n", 200)
    assert tie.allowed("OAI-SearchBot", "https://example.com/")
    separated = RobotsPolicy("User-agent: Googlebot\n\nUser-agent: *\nDisallow: /\n", 200)
    assert separated.allowed("Googlebot", "https://example.com/")
    assert not separated.allowed("SanneticVisionBot/1.0", "https://example.com/")
