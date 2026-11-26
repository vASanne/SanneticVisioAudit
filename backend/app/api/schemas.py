"""Request and response models."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain import AuditState, CheckStatus, Severity

_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[A-Za-z0-9-]{2,63}$")
_CRAWL_BOOLS = ("follow_links", "render_js", "probe_internal_links", "llm_summary")


class AuditCreate(BaseModel):
    """Input for a new audit."""

    url: str = Field(min_length=4, max_length=2000)
    max_pages: int = Field(default=25, ge=1, le=500)
    follow_links: bool = True
    render_js: bool = False
    probe_internal_links: bool = True
    llm_summary: bool = False
    client_name: str = Field(default="Intern", min_length=1, max_length=200)
    client_id: UUID | None = None


class PageRead(BaseModel):
    id: UUID
    url: str
    final_url: str | None
    status_code: int | None
    title: str | None


class IssueRead(BaseModel):
    id: UUID
    check_id: str
    severity: Severity
    title: str
    description: str
    recommendation: str
    affected_urls: list[str]
    status: CheckStatus
    quick_win: bool
    impact_score: float | None = None


class ScoreRead(BaseModel):
    category: str
    score: float
    details: dict[str, Any]


class AuditSummary(BaseModel):
    id: UUID
    client_name: str
    client_id: UUID | None = None
    url: str
    status: AuditState
    created_at: datetime
    finished_at: datetime | None
    pages_crawled: int
    overall_score: float | None
    seo_score: float | None
    geo_score: float | None


class AuditDetail(AuditSummary):
    started_at: datetime | None
    error_message: str | None
    pages: list[PageRead]
    issues: list[IssueRead]
    scores: list[ScoreRead]
    llm_summary: str | None = None
    gsc_notes: list[str] = Field(default_factory=list)


class ClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    domain: str | None = Field(default=None, max_length=255)
    logo_url: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)


class ClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    domain: str | None = None
    logo_url: str | None = None
    settings: dict[str, Any] | None = None


class ClientRead(BaseModel):
    id: UUID
    name: str
    domain: str | None
    logo_url: str | None
    settings: dict[str, Any]
    created_at: datetime


def _email(value: str) -> str:
    text = value.strip().lower()
    if not _EMAIL.match(text):
        raise ValueError("E-Mail ist ungültig")
    return text


def _crawl_config(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("config must be an object")
    unknown = set(value) - {"max_pages", *_CRAWL_BOOLS}
    if unknown:
        raise ValueError("config contains unsupported fields")
    cleaned: dict[str, Any] = {}
    if "max_pages" in value:
        pages = value["max_pages"]
        if isinstance(pages, bool) or not isinstance(pages, int) or not 1 <= pages <= 500:
            raise ValueError("max_pages must be an integer from 1 to 500")
        cleaned["max_pages"] = pages
    for key in _CRAWL_BOOLS:
        if key not in value:
            continue
        if not isinstance(value[key], bool):
            raise ValueError(f"{key} must be a boolean")
        cleaned[key] = value[key]
    return cleaned


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=200)

    @field_validator("email")
    @classmethod
    def email_shape(cls, value: str) -> str:
        return _email(value)


class CsrfToken(BaseModel):
    """Double-submit token. This is not a session credential."""

    csrf_token: str = Field(min_length=32, max_length=128)


class LoginResponse(BaseModel):
    user_name: str
    email: str
    is_admin: bool
    csrf_token: str = Field(min_length=32, max_length=128)


class AuthStatus(BaseModel):
    auth_required: bool
    authenticated: bool
    user_name: str | None = None
    email: str | None = None
    is_admin: bool = False


_API_SCOPES = ("audits:create", "audits:read")


def _api_scopes(value: list[str]) -> list[str]:
    if not value:
        raise ValueError("Mindestens ein Scope ist erforderlich.")
    cleaned: list[str] = []
    for item in value:
        if item not in _API_SCOPES:
            raise ValueError("Unbekannter Scope.")
        if item not in cleaned:
            cleaned.append(item)
    return cleaned


def _future_expiry(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    if value <= datetime.now(timezone.utc):
        raise ValueError("Ablaufzeit muss in der Zukunft liegen.")
    return value


class UserCreate(BaseModel):
    email: str | None = None
    name: str = Field(min_length=1, max_length=200)
    password: str | None = None
    is_admin: bool = False
    is_api_user: bool = False
    client_ids: list[UUID] = Field(default_factory=list)
    scopes: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None

    @field_validator("email")
    @classmethod
    def email_shape(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return _email(value)

    @field_validator("password")
    @classmethod
    def password_length(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not 8 <= len(value) <= 200:
            raise ValueError("Passwort muss 8 bis 200 Zeichen haben.")
        return value

    @field_validator("expires_at")
    @classmethod
    def expiry_future(cls, value: datetime | None) -> datetime | None:
        return _future_expiry(value)

    @model_validator(mode="after")
    def login_or_api(self) -> UserCreate:
        if self.is_api_user:
            if self.is_admin:
                raise ValueError("API-Nutzer können keine Administratoren sein.")
            if self.password:
                raise ValueError("API-Nutzer haben kein Passwort.")
            if len(self.client_ids) != 1:
                raise ValueError("Ein API-Nutzer braucht genau einen Mandanten.")
            self.scopes = _api_scopes(list(self.scopes) or ["audits:create", "audits:read"])
            return self
        if not self.email or not self.password:
            raise ValueError("E-Mail und Passwort sind erforderlich.")
        return self


class UserUpdate(BaseModel):
    email: str | None = Field(default=None, min_length=3, max_length=320)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    password: str | None = Field(default=None, min_length=8, max_length=200)
    is_admin: bool | None = None
    client_ids: list[UUID] | None = None

    @field_validator("email")
    @classmethod
    def email_shape(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _email(value)


class ApiKeyRead(BaseModel):
    """Key metadata. The secret and its hash are not part of this model."""

    id: UUID
    key_id: str
    client_id: UUID
    scopes: list[str]
    expires_at: datetime | None
    revoked_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime


class ApiCredential(BaseModel):
    """Returned once, at creation or rotation. Callers must store ``secret`` themselves."""

    key_id: str
    secret: str = Field(description="Shown once. Only a peppered HMAC is stored. This value cannot be retrieved again.")


class UserRead(BaseModel):
    id: UUID
    email: str | None
    name: str
    is_admin: bool
    is_api_user: bool = False
    client_ids: list[UUID]
    api_keys: list[ApiKeyRead] = Field(default_factory=list)
    created_at: datetime


class UserCreated(UserRead):
    api_credential: ApiCredential | None = None


class ApiKeyCreate(BaseModel):
    user_id: UUID
    scopes: list[str] = Field(default_factory=lambda: ["audits:create", "audits:read"])
    expires_at: datetime | None = None

    @field_validator("scopes")
    @classmethod
    def scope_names(cls, value: list[str]) -> list[str]:
        return _api_scopes(value)

    @field_validator("expires_at")
    @classmethod
    def expiry_future(cls, value: datetime | None) -> datetime | None:
        return _future_expiry(value)


class ApiKeyCreated(ApiKeyRead):
    secret: str = Field(description="Shown once. Only a peppered HMAC is stored.")


def _validate_cron(value: str) -> str:
    parts = value.split()
    if len(parts) not in {5, 6}:
        raise ValueError("cron needs five fields, e.g. 0 6 * * *")
    minute, hour = parts[0], parts[1]
    if not minute.isdigit() or not hour.isdigit():
        raise ValueError("nur feste Stunde/Minute werden unterstützt, z. B. 0 6 * * *")
    if not 0 <= int(minute) <= 59 or not 0 <= int(hour) <= 23:
        raise ValueError("cron Stunde/Minute außerhalb des gültigen Bereichs")
    return value


class ScheduleCreate(BaseModel):
    client_id: UUID
    url: str = Field(min_length=4, max_length=2000)
    cron: str = Field(default="0 6 * * *", max_length=64)
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("cron")
    @classmethod
    def cron_parts(cls, value: str) -> str:
        return _validate_cron(value)

    @field_validator("config")
    @classmethod
    def crawl_config(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _crawl_config(value)


class ScheduleUpdate(BaseModel):
    url: str | None = Field(default=None, min_length=4, max_length=2000)
    cron: str | None = Field(default=None, max_length=64)
    enabled: bool | None = None
    config: dict[str, Any] | None = None

    @field_validator("cron")
    @classmethod
    def cron_parts(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_cron(value)

    @field_validator("config")
    @classmethod
    def crawl_config(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return None
        return _crawl_config(value)


class ScheduleRead(BaseModel):
    id: UUID
    client_id: UUID
    client_name: str
    url: str
    cron: str
    enabled: bool
    config: dict[str, Any]
    last_run_at: datetime | None
    next_run_at: datetime | None
    created_at: datetime


class WatchlistCreate(BaseModel):
    client_id: UUID
    url: str = Field(min_length=4, max_length=2000)
    label: str = Field(default="", max_length=200)
    notes: str = Field(default="", max_length=4000)
    enabled: bool = True
    renew_enabled: bool = False
    cron: str = Field(default="0 6 * * *", max_length=64)
    config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("cron")
    @classmethod
    def cron_parts(cls, value: str) -> str:
        return _validate_cron(value)

    @field_validator("config")
    @classmethod
    def crawl_config(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _crawl_config(value)


class WatchlistUpdate(BaseModel):
    label: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=4000)
    enabled: bool | None = None
    renew_enabled: bool | None = None
    cron: str | None = Field(default=None, max_length=64)
    config: dict[str, Any] | None = None
    url: str | None = Field(default=None, min_length=4, max_length=2000)

    @field_validator("cron")
    @classmethod
    def cron_parts(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_cron(value)

    @field_validator("config")
    @classmethod
    def crawl_config(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return None
        return _crawl_config(value)


class AgentAuditBatch(BaseModel):
    """One or more public URLs to audit. The tenant comes from the API key, not this body."""

    urls: list[str] = Field(min_length=1, max_length=25)
    max_pages: int = Field(default=25, ge=1, le=500)
    follow_links: bool = True
    render_js: bool = False
    probe_internal_links: bool = True
    llm_summary: bool = False

    @field_validator("urls")
    @classmethod
    def url_lengths(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in value:
            if not isinstance(item, str) or not 4 <= len(item.strip()) <= 2000:
                raise ValueError("Each URL must be between 4 and 2000 characters.")
            cleaned.append(item.strip())
        return cleaned


class AgentAuditAccepted(BaseModel):
    id: UUID
    url: str
    status: str


class AgentAuditBatchResult(BaseModel):
    audits: list[AgentAuditAccepted]


class AgentAuditStatus(BaseModel):
    id: UUID
    url: str
    status: AuditState
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    pages_crawled: int
    overall_score: float | None
    seo_score: float | None
    geo_score: float | None
    error_message: str | None


class WatchlistRead(BaseModel):
    id: UUID
    client_id: UUID
    client_name: str
    url: str
    label: str
    notes: str
    enabled: bool
    schedule_id: UUID | None
    renew_enabled: bool
    cron: str | None
    config: dict[str, Any]
    last_audit_id: UUID | None
    last_overall_score: float | None
    last_checked_at: datetime | None
    next_run_at: datetime | None
    created_at: datetime
