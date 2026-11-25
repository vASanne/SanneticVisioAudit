"""Auth status, users, and watchlist schemas smoke through helpers."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.schemas import ScheduleCreate, WatchlistCreate, WatchlistUpdate
from app.core.config import get_settings
from app.core.security import AuthUser, hash_password, issue_token, parse_token, verify_password
from app.services.schedule_service import next_run_after


def test_user_password_and_token_for_admin_ui(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "auth_secret", "y" * 32)
    digest = hash_password("correct-horse-1")
    assert verify_password("correct-horse-1", digest)
    user = AuthUser(id=uuid4(), email="admin@example.com", name="Sannetic", is_admin=True)
    token = issue_token(user)
    parsed = parse_token(token)
    assert parsed is not None
    assert parsed.is_admin is True


def test_watchlist_and_schedule_cron_validators() -> None:
    schedule = ScheduleCreate(client_id=uuid4(), url="https://example.com/", cron="30 7 * * *")
    assert schedule.cron == "30 7 * * *"
    item = WatchlistCreate(client_id=uuid4(), url="https://example.com/blog", renew_enabled=True, cron="0 6 * * *")
    assert item.renew_enabled is True
    nxt = next_run_after("0 6 * * *", datetime(2026, 11, 15, 5, 0, tzinfo=timezone.utc))
    assert nxt.hour == 6


def test_schedule_config_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ScheduleCreate(
            client_id=uuid4(),
            url="https://example.com/",
            config={"max_pages": 10, "command": "rm"},
        )


def test_watchlist_update_can_pause_renewal_without_dropping_cron() -> None:
    payload = WatchlistUpdate(renew_enabled=False, cron="15 8 * * *")
    assert payload.renew_enabled is False
    assert payload.cron == "15 8 * * *"
