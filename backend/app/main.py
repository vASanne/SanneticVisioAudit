"""FastAPI application."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.audits import router as audit_router
from app.api.routes.auth import ensure_agency_admin, router as auth_router
from app.api.routes.clients import router as client_router
from app.api.routes.health import router as health_router
from app.api.routes.schedules import router as schedule_router
from app.api.routes.users import router as user_router
from app.api.routes.watchlist import router as watchlist_router
from app.core.config import get_settings
from app.core.database import session_scope
from app.core.http_security import SecurityMiddleware, checked_origins
from app.core.logging import setup_logging
from app.core.security import auth_enabled

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    settings = get_settings()
    if settings.debug:
        logger.warning("debug_flag_set")
    if not auth_enabled():
        logger.warning("auth_disabled")
    elif len(settings.auth_secret.strip()) < 32:
        logger.warning("auth_secret_missing")
    if not settings.database_url.strip():
        logger.warning("database_url_missing")
    else:
        with session_scope() as db:
            ensure_agency_admin(db)
    yield


def create_app() -> FastAPI:
    """Build the API. Interactive docs stay off unless EXPOSE_DOCS is set."""

    settings = get_settings()
    origins = checked_origins(settings.cors_origin_list)
    docs = "/docs" if settings.expose_docs else None
    app = FastAPI(
        title=settings.app_name,
        version="0.2.0",
        description="SEO- und GEO-Audits mit nachvollziehbaren Checks und Scores.",
        lifespan=lifespan,
        debug=False,
        docs_url=docs,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.expose_docs else None,
    )
    app.add_middleware(SecurityMiddleware, allowed_origins=origins)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
        max_age=600,
    )
    app.include_router(health_router)
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(user_router, prefix="/api/v1")
    app.include_router(client_router, prefix="/api/v1")
    app.include_router(watchlist_router, prefix="/api/v1")
    app.include_router(schedule_router, prefix="/api/v1")
    app.include_router(audit_router, prefix="/api/v1")

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        detail = [
            {"loc": list(item.get("loc", ())), "msg": str(item.get("msg", "Ungültige Eingabe")), "type": item.get("type")}
            for item in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": detail})

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, HTTPException):
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=dict(exc.headers or {}))
        logger.exception("unhandled_error")
        return JSONResponse(status_code=500, content={"detail": "Interner Fehler."})

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {"service": "sannetic-vision-audit", "docs": docs or "", "health": "/health"}

    return app


app = create_app()
