"""Shared fixtures. Rate limits use an in-process Redis stand-in, not a live server."""

from __future__ import annotations

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles

import pytest

from app.core import rate_limit


@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(_type: JSONB, _compiler: object, **_kwargs: object) -> str:
    """Let sqlite tests create tables that use JSONB in production."""

    return "JSON"


@pytest.fixture(autouse=True)
def redis_rate_limit() -> object:
    fakeredis = pytest.importorskip("fakeredis")
    client = fakeredis.FakeRedis(server=fakeredis.FakeServer(), decode_responses=True)
    rate_limit.set_client(client)
    yield client
    rate_limit.set_client(None)
