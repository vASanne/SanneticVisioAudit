"""In-process sliding-window rate limit.

The API image runs a single uvicorn process, so this window is enough for the
default deployment. Several API processes would each keep their own window.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

_LOCK = threading.Lock()
_HITS: dict[str, deque[float]] = defaultdict(deque)


def allow(key: str, *, limit: int, window_seconds: float) -> bool:
    """Record one hit. Return False when the key is already over the limit."""

    now = time.monotonic()
    with _LOCK:
        hits = _HITS[key]
        cutoff = now - window_seconds
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(now)
        return True


def reset() -> None:
    """Drop every window. Used by tests."""

    with _LOCK:
        _HITS.clear()
