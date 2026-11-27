"""Public URL checks for the crawler.

Every fetch goes through this module: the initial URL, redirects, and the
address the socket actually opens. Obfuscated IP spellings are rejected before
DNS so a client cannot disagree with the checker.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from collections.abc import Callable
from typing import cast
from urllib.parse import urlsplit

from app.crawler.errors import UnsafeUrlError

# DNS lookup tests replace. Production calls it as resolver(host, None).
Resolver = Callable[[str, int | None], list[tuple[object, ...]]]


def _default_resolver(host: str, port: int | None, *_args: object, **_kwargs: object) -> list[tuple[object, ...]]:
    return cast(list[tuple[object, ...]], socket.getaddrinfo(host, port))


_BLOCKED_NAMES = {
    "localhost",
    "localhost.localdomain",
    "metadata",
    "metadata.google.internal",
    "metadata.goog",
    "instance-data",
    "kubernetes",
    "kubernetes.default",
    "kubernetes.default.svc",
}
_BLOCKED_SUFFIXES = (
    ".local",
    ".localhost",
    ".internal",
    ".localdomain",
    ".intranet",
    ".lan",
    ".home.arpa",
)
_BLOCKED_NETWORKS = tuple(
    ipaddress.ip_network(item)
    for item in (
        "0.0.0.0/8",
        "10.0.0.0/8",
        "100.64.0.0/10",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.0.0.0/24",
        "192.0.2.0/24",
        "192.168.0.0/16",
        "198.18.0.0/15",
        "198.51.100.0/24",
        "203.0.113.0/24",
        "224.0.0.0/4",
        "240.0.0.0/4",
        "::/128",
        "::1/128",
        "fc00::/7",
        "fe80::/10",
        "2001:db8::/32",
    )
)
_DOTTED_NUMBERS = re.compile(r"^(\d{1,10})(\.\d{1,10}){0,3}$")
_HEX_IP = re.compile(r"^(0x[0-9a-f]+)(\.0x[0-9a-f]+)*$", re.IGNORECASE)


def assert_public_url(url: str, *, resolver: Resolver = _default_resolver) -> None:
    """Reject non-public hosts so the crawler cannot be aimed at the internal network."""

    if not url or "\\" in url or "\x00" in url or "%00" in url.lower() or "%0a" in url.lower() or "%0d" in url.lower():
        raise UnsafeUrlError("Nur öffentliche http- und https-Adressen können geprüft werden.")
    parts = urlsplit(url.strip())
    if parts.username is not None or parts.password is not None:
        raise UnsafeUrlError("URLs mit Zugangsdaten sind nicht erlaubt.")
    host = (parts.hostname or "").lower().rstrip(".")
    if not host or parts.scheme not in {"http", "https"}:
        raise UnsafeUrlError("Nur öffentliche http- und https-Adressen können geprüft werden.")
    try:
        port = parts.port
    except ValueError as exc:
        raise UnsafeUrlError("Der Port ist ungültig.") from exc
    if port == 0:
        raise UnsafeUrlError("Der Port ist ungültig.")
    if _blocked_hostname(host):
        raise UnsafeUrlError("Nur öffentliche Web-Adressen können geprüft werden.")
    public_connect_host(host, resolver=resolver)


def public_connect_host(host: str, *, resolver: Resolver = _default_resolver) -> str:
    """Return one public address for this host. Every resolved address must be public."""

    name = host.lower().rstrip(".")
    if _blocked_hostname(name):
        raise UnsafeUrlError("Nur öffentliche Web-Adressen können geprüft werden.")
    addresses = _addresses(name, resolver)
    if any(not _is_public_ip(address) for address in addresses):
        raise UnsafeUrlError("Nur öffentliche Web-Adressen können geprüft werden.")
    return str(addresses[0])


def logo_reference_is_safe(url: str) -> bool:
    """True for an http(s) logo that is not an obvious internal address.

    Hostnames are not resolved here. Saving a logo still resolves it. Rendering
    a stored logo does not open a server-side connection to that host.
    """

    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return False
    host = (parts.hostname or "").lower().rstrip(".")
    if parts.scheme not in {"http", "https"} or not host or parts.username or parts.password:
        return False
    if _blocked_hostname(host):
        return False
    literal = _literal_address(host)
    return literal is None or _is_public_ip(literal)


def _blocked_hostname(host: str) -> bool:
    if not host or host in _BLOCKED_NAMES or host.endswith(_BLOCKED_SUFFIXES):
        return True
    if "%" in host or _HEX_IP.match(host):
        return True
    return _obfuscated_decimal(host)


def _obfuscated_decimal(host: str) -> bool:
    if not _DOTTED_NUMBERS.match(host):
        return False
    parts = host.split(".")
    if len(parts) != 4:
        return True
    for part in parts:
        if len(part) > 1 and part.startswith("0"):
            return True
        if int(part) > 255:
            return True
    return False


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
        if len(info) < 5:
            continue
        sockaddr = info[4]
        if not isinstance(sockaddr, tuple) or not sockaddr:
            continue
        raw = sockaddr[0]
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


def _is_public_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    if (
        ip.is_multicast
        or ip.is_reserved
        or ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_unspecified
        or not ip.is_global
    ):
        return False
    return not any(ip in network for network in _BLOCKED_NETWORKS)
