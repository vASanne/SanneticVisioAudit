"""Environment configuration.

Secrets have no defaults. Set them in the process environment (Compose reads
``VisioAudit-Infra/.env``) before any shared or production deployment.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from the environment."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Sannetic Vision Audit"
    database_url: str = ""
    redis_url: str = "redis://127.0.0.1:6379/0"
    celery_broker_url: str = "redis://127.0.0.1:6379/0"
    s3_endpoint: str = "http://127.0.0.1:9000"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "audits"
    user_agent: str = "SanneticVisionBot/1.0 (+https://sannetic.com/bot)"
    crawl_delay_seconds: float = 0.5
    max_pages_cap: int = 500
    max_link_probes: int = 200
    cors_origins: str = "http://127.0.0.1:3000,http://localhost:3000"
    log_level: str = "INFO"
    log_format: str = "console"
    pagespeed_api_key: str = ""
    auth_secret: str = ""
    auth_disabled: bool = False
    # Secure cookies are the default. Local HTTP (compose.override) sets this false.
    cookie_secure: bool = True
    cookie_samesite: str = "lax"
    expose_docs: bool = False
    debug: bool = False
    agency_email: str = ""
    agency_password: str = ""
    agency_name: str = "Agentur"
    gsc_access_token: str = ""
    llm_api_key: str = ""
    llm_api_url: str = "https://api.openai.com/v1/chat/completions"
    llm_model: str = "gpt-4o-mini"

    @field_validator("cookie_samesite")
    @classmethod
    def cookie_samesite_choice(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in {"lax", "strict"}:
            raise ValueError("COOKIE_SAMESITE must be lax or strict")
        return cleaned

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""

    return Settings()
