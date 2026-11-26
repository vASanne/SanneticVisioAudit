"""Public routing: Caddy forwards /api unchanged, so routes stay under that prefix."""

from fastapi.routing import APIRoute

from app.core.config import get_settings
from app.main import app


def _paths() -> set[str]:
    found = {route.path for route in app.routes if isinstance(route, APIRoute)}
    for route in app.routes:
        context = getattr(route, "include_context", None)
        router = getattr(route, "original_router", None)
        if context is None or router is None:
            continue
        prefix = context.prefix or ""
        found.update(prefix + child.path for child in router.routes)
    return found


def test_routes_stay_under_the_public_api_prefix() -> None:
    paths = _paths()
    assert "/health" in paths
    assert "/api/v1/health" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/audits" in paths
    assert all(path in {"/", "/health"} or path.startswith("/api/") for path in paths)


def test_root_path_is_empty_unless_a_proxy_strips_the_prefix(monkeypatch) -> None:
    """Uvicorn receives ROOT_PATH only when a proxy strips /api. Default is empty."""

    assert get_settings().root_path == ""
    monkeypatch.setenv("ROOT_PATH", "/api")
    get_settings.cache_clear()
    try:
        assert get_settings().root_path == "/api"
    finally:
        get_settings.cache_clear()
