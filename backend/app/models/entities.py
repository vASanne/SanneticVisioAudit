"""Persistence models for clients, audits, pages, issues, and scores."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def utcnow() -> datetime:
    """Timezone-aware timestamp for ORM defaults."""

    return datetime.now(timezone.utc)


class User(Base):
    """Agency login that can access one or more clients."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(Text)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), default=utcnow)

    memberships: Mapped[list[Membership]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Membership(Base):
    """Which clients a user may see."""

    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "client_id", name="uq_membership_user_client"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(32), default="member", server_default="member")

    user: Mapped[User] = relationship(back_populates="memberships")
    client: Mapped[Client] = relationship(back_populates="memberships")


class Client(Base):
    """Agency client that owns audits."""

    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    domain: Mapped[str | None] = mapped_column(String(255), default=None)
    logo_url: Mapped[str | None] = mapped_column(Text, default=None)
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), default=utcnow)

    audits: Mapped[list[Audit]] = relationship(back_populates="client")
    memberships: Mapped[list[Membership]] = relationship(back_populates="client", cascade="all, delete-orphan")
    schedules: Mapped[list[AuditSchedule]] = relationship(back_populates="client", cascade="all, delete-orphan")
    watchlist_items: Mapped[list[WatchlistItem]] = relationship(back_populates="client", cascade="all, delete-orphan")


class Audit(Base):
    """One crawl-and-score run for a start URL."""

    __tablename__ = "audits"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    url: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="pending", server_default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), default=utcnow)
    pages_crawled: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    overall_score: Mapped[float | None] = mapped_column(Float, default=None)
    seo_score: Mapped[float | None] = mapped_column(Float, default=None)
    geo_score: Mapped[float | None] = mapped_column(Float, default=None)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)

    client: Mapped[Client] = relationship(back_populates="audits")
    pages: Mapped[list[Page]] = relationship(back_populates="audit", cascade="all, delete-orphan", order_by="Page.position")
    issues: Mapped[list[Issue]] = relationship(back_populates="audit", cascade="all, delete-orphan")
    scores: Mapped[list[Score]] = relationship(back_populates="audit", cascade="all, delete-orphan")


class Page(Base):
    """A fetched URL and the facts extracted from its HTML."""

    __tablename__ = "pages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    audit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("audits.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    url: Mapped[str] = mapped_column(Text)
    final_url: Mapped[str | None] = mapped_column(Text, default=None)
    status_code: Mapped[int | None] = mapped_column(Integer, default=None)
    title: Mapped[str | None] = mapped_column(Text, default=None)
    meta_description: Mapped[str | None] = mapped_column(Text, default=None)
    content_hash: Mapped[str | None] = mapped_column(String(64), default=None)
    html_storage_path: Mapped[str | None] = mapped_column(Text, default=None)
    extract: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    crawled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), default=utcnow)

    audit: Mapped[Audit] = relationship(back_populates="pages")


class Issue(Base):
    """A failed or warning check, with a customer-facing fix."""

    __tablename__ = "issues"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    audit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("audits.id", ondelete="CASCADE"), index=True)
    page_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pages.id", ondelete="SET NULL"), default=None)
    check_id: Mapped[str] = mapped_column(String(16))
    severity: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str] = mapped_column(Text)
    affected_urls: Mapped[list[str]] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(16))
    quick_win: Mapped[bool] = mapped_column(default=False, server_default="false")

    audit: Mapped[Audit] = relationship(back_populates="issues")


class Score(Base):
    """Category score plus the weights that produced it."""

    __tablename__ = "scores"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    audit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("audits.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(32))
    score: Mapped[float] = mapped_column(Float)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    audit: Mapped[Audit] = relationship(back_populates="scores")


class AuditSchedule(Base):
    """Recurring crawl for one client URL."""

    __tablename__ = "audit_schedules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(Text)
    cron: Mapped[str] = mapped_column(String(64), default="0 6 * * *", server_default="0 6 * * *")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), default=utcnow)

    client: Mapped[Client] = relationship(back_populates="schedules")
    watchlist_items: Mapped[list[WatchlistItem]] = relationship(back_populates="schedule")


class WatchlistItem(Base):
    """Customer URL under observation, optionally with a renewal schedule."""

    __tablename__ = "watchlist_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(Text)
    label: Mapped[str] = mapped_column(String(200), default="", server_default="")
    notes: Mapped[str] = mapped_column(Text, default="", server_default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    schedule_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("audit_schedules.id", ondelete="SET NULL"),
        default=None,
        index=True,
    )
    last_audit_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("audits.id", ondelete="SET NULL"), default=None)
    last_overall_score: Mapped[float | None] = mapped_column(Float, default=None)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), default=utcnow)

    client: Mapped[Client] = relationship(back_populates="watchlist_items")
    schedule: Mapped[AuditSchedule | None] = relationship(back_populates="watchlist_items")
