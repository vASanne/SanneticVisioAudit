"""FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.audits import router as audit_router
from app.api.routes.auth import ensure_agency_admin, router as auth_router
from app.api.routes.clients import router as client_router
from app.api.routes.health import router as health_router
from app.api.routes.schedules import router as schedule_router
from app.api.routes.users import router as user_router
from app.api.routes.watchlist import router as watchlist_router
from app.core.config import get_settings
from app.core.database import session_scope
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    with session_scope() as db:
        ensure_agency_admin(db)
    yield


def create_app() -> FastAPI:
    """Build the API, including OpenAPI docs and the audit routes."""

    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.2.0",
        description="SEO- und GEO-Audits mit nachvollziehbaren Checks und Scores.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(user_router, prefix="/api/v1")
    app.include_router(client_router, prefix="/api/v1")
    app.include_router(watchlist_router, prefix="/api/v1")
    app.include_router(schedule_router, prefix="/api/v1")
    app.include_router(audit_router, prefix="/api/v1")

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {"service": "sannetic-vision-audit", "docs": "/docs", "health": "/health"}

    return app


app = create_app()
