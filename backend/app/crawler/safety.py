"""Public URL checks for the crawler."""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable
from urllib.parse import urlsplit

from app.crawler.errors import UnsafeUrlError

Resolver = Callable[..., list[tuple[object, ...]]]

_BLOCKED_NAMES = {"localhost", "localhost.localdomain", "metadata.google.internal"}


def assert_public_url(url: str, *, resolver: Resolver = socket.getaddrinfo) -> None:
    """Reject non-public hosts so the crawler cannot be aimed at the internal network."""

    parts = urlsplit(url)
    host = (parts.hostname or "").lower().rstrip(".")
    if not host or parts.scheme not in {"http", "https"}:
        raise UnsafeUrlError("Nur öffentliche http- und https-Adressen können geprüft werden.")
    public_connect_host(host, resolver=resolver)


def public_connect_host(host: str, *, resolver: Resolver = socket.getaddrinfo) -> str:
    """Return one public address for this host. Every resolved address must be public."""

    name = host.lower().rstrip(".")
    if not name or name in _BLOCKED_NAMES or name.endswith(".local") or name.endswith(".internal"):
        raise UnsafeUrlError("Nur öffentliche Web-Adressen können geprüft werden.")
    addresses = _addresses(name, resolver)
    if any(not address.is_global for address in addresses):
        raise UnsafeUrlError("Nur öffentliche Web-Adressen können geprüft werden.")
    return str(addresses[0])


def _addresses(host: str, resolver: Resolver) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    literal = _literal_address(host)
    if literal is not None:
        return [literal]
    try:
        infos = resolver(host, None)
    except socket.gaierror as exc:
        raise UnsafeUrlError("Der Hostname konnte nicht aufgelöst werden.") from exc
    addresses: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for info in infos:
        raw = info[4][0]
        if not isinstance(raw, str):
            continue
        parsed = _literal_address(raw.split("%", 1)[0])
        if parsed is not None:
            addresses.append(parsed)
    if not addresses:
        raise UnsafeUrlError("Der Hostname konnte nicht aufgelöst werden.")
    return addresses


def _literal_address(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        parsed = ipaddress.ip_address(value)
    except ValueError:
        return None
    if isinstance(parsed, ipaddress.IPv6Address) and parsed.ipv4_mapped is not None:
        return parsed.ipv4_mapped
    return parsed
