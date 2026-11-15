"""The crawler only accepts public web URLs."""

import socket

import pytest

from app.crawler.errors import UnsafeUrlError
from app.crawler.safety import assert_public_url
from app.crawler.urls import crawl_key, normalize_start_url, same_site


def _public(host: str, _port: object, *args: object, **kwargs: object) -> list[tuple[object, ...]]:
    if host != "example.com":
        raise socket.gaierror(host)
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]


def _private(host: str, _port: object, *args: object, **kwargs: object) -> list[tuple[object, ...]]:
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


def test_private_and_local_targets_are_rejected() -> None:
    with pytest.raises(UnsafeUrlError):
        assert_public_url("http://127.0.0.1/", resolver=_unused)
    with pytest.raises(UnsafeUrlError):
        assert_public_url("http://169.254.169.254/", resolver=_unused)
    with pytest.raises(UnsafeUrlError):
        assert_public_url("http://localhost/admin", resolver=_unused)
    with pytest.raises(UnsafeUrlError):
        assert_public_url("https://example.com/", resolver=_private)


def test_same_site_ignores_www_and_crawl_key_ignores_query() -> None:
    assert same_site("https://www.example.com/a", "https://example.com/b")
    assert not same_site("https://example.com/", "https://other.example/")
    assert crawl_key("https://example.com/pfad/?utm=1") == crawl_key("https://example.com/pfad")
