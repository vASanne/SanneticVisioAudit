"""Request and response models."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain import AuditState, CheckStatus, Severity


class AuditCreate(BaseModel):
    """Input for a new audit."""

    url: str = Field(min_length=4, max_length=2000)
    max_pages: int = Field(default=25, ge=1, le=100)
    follow_links: bool = True
    client_name: str = Field(default="Intern", min_length=1, max_length=200)


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


class ScoreRead(BaseModel):
    category: str
    score: float
    details: dict[str, Any]


class AuditSummary(BaseModel):
    id: UUID
    client_name: str
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
