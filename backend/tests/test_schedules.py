"""Daily cron helpers for recurring audits."""

from datetime import UTC, datetime

import pytest
from app.services.schedule_service import next_run_after


def test_next_run_after_daily_rolls_forward() -> None:
    moment = datetime(2026, 11, 15, 7, 0, tzinfo=UTC)
    assert next_run_after("0 6 * * *", moment) == datetime(2026, 11, 16, 6, 0, tzinfo=UTC)
    earlier = datetime(2026, 11, 15, 5, 0, tzinfo=UTC)
    assert next_run_after("0 6 * * *", earlier) == datetime(2026, 11, 15, 6, 0, tzinfo=UTC)


def test_next_run_after_rejects_wildcards() -> None:
    moment = datetime(2026, 11, 15, 7, 0, tzinfo=UTC)
    with pytest.raises(ValueError):
        next_run_after("*/5 * * * *", moment)
