"""Client settings stay on an allow-list and do not echo secrets."""

import pytest
from app.core.client_settings import SettingsRejected, public_client_settings, sanitize_client_settings


def test_settings_drop_unknown_keys_and_hide_the_token() -> None:
    placeholder = "super-secret-token"
    stored = sanitize_client_settings(
        {
            "white_label": True,
            "css_vars": {"--color-primary": "#112233"},
            "important_paths": ["/blog"],
            "gsc_access_token": placeholder,
            "shell": "id",
        },
        existing=None,
        is_admin=True,
    )
    assert "shell" not in stored
    assert stored["gsc_access_token"] == placeholder
    visible = public_client_settings(stored)
    assert "gsc_access_token" not in visible
    assert visible["gsc_token_configured"] is True
    assert "super-secret-token" not in str(visible)


def test_member_cannot_replace_or_inject_the_token() -> None:
    stored = "stored-token-value"
    existing = {"gsc_access_token": stored, "white_label": False}
    updated = sanitize_client_settings(
        {"white_label": True, "gsc_access_token": "injected-token-value"},
        existing=existing,
        is_admin=False,
    )
    assert updated["gsc_access_token"] == stored
    assert updated["white_label"] is True


def test_css_and_paths_are_rejected() -> None:
    with pytest.raises(SettingsRejected):
        sanitize_client_settings(
            {"css_vars": {"--color-primary": "url(https://evil.example/x)"}}, existing=None, is_admin=True
        )
    with pytest.raises(SettingsRejected):
        sanitize_client_settings({"important_paths": ["https://evil.example/"]}, existing=None, is_admin=True)
