"""Request and response models."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.domain import AuditState, CheckStatus, Severity


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


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=200)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_name: str
    email: str
    is_admin: bool


class AuthStatus(BaseModel):
    auth_required: bool
    authenticated: bool
    user_name: str | None = None
    email: str | None = None
    is_admin: bool = False


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=200)
    is_admin: bool = False
    client_ids: list[UUID] = Field(default_factory=list)


class UserUpdate(BaseModel):
    email: str | None = Field(default=None, min_length=3, max_length=320)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    password: str | None = Field(default=None, min_length=8, max_length=200)
    is_admin: bool | None = None
    client_ids: list[UUID] | None = None


class UserRead(BaseModel):
    id: UUID
    email: str
    name: str
    is_admin: bool
    client_ids: list[UUID]
    created_at: datetime


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
    notes: str = ""
    enabled: bool = True
    renew_enabled: bool = False
    cron: str = Field(default="0 6 * * *", max_length=64)
    config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("cron")
    @classmethod
    def cron_parts(cls, value: str) -> str:
        return _validate_cron(value)


class WatchlistUpdate(BaseModel):
    label: str | None = Field(default=None, max_length=200)
    notes: str | None = None
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
