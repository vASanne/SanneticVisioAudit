"""Shared sliding-window rate limit backed by Redis.

Every API process uses the same Redis key, so the window is shared across
workers. The check and the increment run in one Lua script, which Redis
executes atomically.

Fail closed: if Redis cannot answer, ``allow`` raises ``RateLimitUnavailable``.
Login and audit start must reject the request (HTTP 503). A silent allow would
turn a Redis outage into an unlimited password-guessing window. Audits already
depend on Redis for the worker queue, so this choice matches that dependency.
The client uses a one-second socket timeout and does not fall open.
"""

from __future__ import annotations

import secrets
import threading

import redis
import structlog

logger = structlog.get_logger()

_LOCK = threading.Lock()
_pool: redis.Redis | None = None
_override: object | None = None

# ARGV: window milliseconds, limit, unique member.
# TIME comes from Redis so workers do not need a shared clock.
_SLIDING_WINDOW = """
local time = redis.call('TIME')
local now = tonumber(time[1]) * 1000 + math.floor(tonumber(time[2]) / 1000)
local window = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local member = ARGV[3]
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - window)
local count = redis.call('ZCARD', KEYS[1])
if count >= limit then
  redis.call('PEXPIRE', KEYS[1], window)
  return 0
end
redis.call('ZADD', KEYS[1], now, member)
redis.call('PEXPIRE', KEYS[1], window)
return 1
"""


class RateLimitUnavailable(RuntimeError):
    """The shared limiter could not be reached. Callers must fail closed."""


def allow(key: str, *, limit: int, window_seconds: float) -> bool:
    """Record one hit. Return False when the key is already over the limit."""

    if limit < 1 or window_seconds <= 0:
        return False
    client = _client()
    window_ms = max(1, int(window_seconds * 1000))
    member = secrets.token_hex(16)
    try:
        result = client.eval(_SLIDING_WINDOW, 1, f"rl:{key}", str(window_ms), str(limit), member)
    except (redis.RedisError, OSError) as exc:
        logger.warning("rate_limit_unavailable", error_type=type(exc).__name__)
        raise RateLimitUnavailable("rate limit store unavailable") from exc
    if isinstance(result, bytes):
        result = result.decode("ascii")
    return int(result) == 1


def set_client(client: object | None) -> None:
    """Replace the Redis client. Tests inject a fake; production leaves this unset."""

    global _override
    _override = client


def reset() -> None:
    """Drop limiter keys on the injected client. Used by tests."""

    client = _override if _override is not None else _pool
    if client is None or not hasattr(client, "scan_iter"):
        return
    for key in client.scan_iter(match="rl:*"):
        client.delete(key)


def _client() -> object:
    if _override is not None:
        return _override
    global _pool
    if _pool is None:
        with _LOCK:
            if _pool is None:
                from app.core.config import get_settings

                _pool = redis.Redis.from_url(
                    get_settings().redis_url,
                    socket_timeout=1.0,
                    socket_connect_timeout=1.0,
                    health_check_interval=30,
                    decode_responses=True,
                )
    return _pool
