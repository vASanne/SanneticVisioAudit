"""Shared fixtures. Rate limits use an in-process Redis stand-in, not a live server."""

from __future__ import annotations

import pytest

from app.core import rate_limit


@pytest.fixture(autouse=True)
def redis_rate_limit() -> object:
    fakeredis = pytest.importorskip("fakeredis")
    client = fakeredis.FakeRedis(server=fakeredis.FakeServer(), decode_responses=True)
    rate_limit.set_client(client)
    yield client
    rate_limit.set_client(None)
