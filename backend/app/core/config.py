"""Environment configuration.

Development defaults match the Compose stack in ``VisioAudit-Infra``. Override them
with environment variables before any shared or production deployment.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from the environment."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Sannetic Vision Audit"
    database_url: str = "postgresql+psycopg://visio:REDACTED@127.0.0.1:5432/visioaudit"
    redis_url: str = "redis://127.0.0.1:6379/0"
    celery_broker_url: str = "redis://127.0.0.1:6379/0"
    s3_endpoint: str = "http://127.0.0.1:9000"
    s3_access_key: str = "visioaudit"
    s3_secret_key: str = "REDACTED"
    s3_bucket: str = "audits"
    user_agent: str = "SanneticVisionBot/1.0 (+https://sannetic.com/bot)"
    crawl_delay_seconds: float = 0.5
    max_pages_cap: int = 100
    cors_origins: str = "http://127.0.0.1:3000,http://localhost:3000"
    log_level: str = "INFO"
    log_format: str = "console"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""

    return Settings()
