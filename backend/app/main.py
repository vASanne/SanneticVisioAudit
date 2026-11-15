"""FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.audits import router as audit_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.logging import setup_logging


def create_app() -> FastAPI:
    """Build the API, including OpenAPI docs and the audit routes."""

    setup_logging()
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="SEO- und GEO-Audits mit nachvollziehbaren Checks und Scores.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(audit_router, prefix="/api/v1")

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {"service": "sannetic-vision-audit", "docs": "/docs", "health": "/health"}

    return app


app = create_app()
