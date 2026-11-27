"""Watchlist of customer URLs with optional report renewal."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import AuthUser, allowed_client_ids, assert_client_access, require_login
from app.api.schemas import WatchlistCreate, WatchlistRead, WatchlistUpdate
from app.core.database import get_db
from app.crawler.errors import UnsafeUrlError
from app.crawler.safety import assert_public_url
from app.crawler.urls import normalize_start_url
from app.models import AuditSchedule, Client, WatchlistItem
from app.services.schedule_service import next_run_after

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=list[WatchlistRead])
def list_watchlist(
    db: Session = Depends(get_db),
    user: AuthUser | None = Depends(require_login),
) -> list[WatchlistRead]:
    query = (
        select(WatchlistItem)
        .options(selectinload(WatchlistItem.client), selectinload(WatchlistItem.schedule))
        .order_by(WatchlistItem.created_at.desc())
    )
    allowed = allowed_client_ids(db, user)
    if allowed is not None:
        if not allowed:
            return []
        query = query.where(WatchlistItem.client_id.in_(allowed))
    return [_read(row) for row in db.scalars(query).all()]


@router.post("", response_model=WatchlistRead, status_code=status.HTTP_201_CREATED)
def create_watchlist_item(
    payload: WatchlistCreate,
    db: Session = Depends(get_db),
    user: AuthUser | None = Depends(require_login),
) -> WatchlistRead:
    assert_client_access(db, user, payload.client_id)
    client = db.get(Client, payload.client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mandant nicht gefunden.")
    try:
        url = normalize_start_url(payload.url)
        assert_public_url(url)
    except UnsafeUrlError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    item = WatchlistItem(
        client_id=payload.client_id,
        url=url,
        label=payload.label.strip(),
        notes=payload.notes.strip(),
        enabled=payload.enabled,
    )
    db.add(item)
    db.flush()
    if payload.renew_enabled:
        _attach_schedule(db, item, cron=payload.cron, config=payload.config, enabled=True)
    db.commit()
    return _reload(db, item.id)


@router.patch("/{item_id}", response_model=WatchlistRead)
def update_watchlist_item(
    item_id: UUID,
    payload: WatchlistUpdate,
    db: Session = Depends(get_db),
    user: AuthUser | None = Depends(require_login),
) -> WatchlistRead:
    item = _get(db, item_id)
    assert_client_access(db, user, item.client_id)
    if payload.url is not None:
        try:
            url = normalize_start_url(payload.url)
            assert_public_url(url)
        except UnsafeUrlError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        item.url = url
        if item.schedule is not None:
            item.schedule.url = url
    if payload.label is not None:
        item.label = payload.label.strip()
    if payload.notes is not None:
        item.notes = payload.notes.strip()
    if payload.enabled is not None:
        item.enabled = payload.enabled
    renew = payload.renew_enabled
    cron = payload.cron
    config = payload.config
    if renew is True:
        _attach_schedule(
            db,
            item,
            cron=cron or (item.schedule.cron if item.schedule else "0 6 * * *"),
            config=config if config is not None else (dict(item.schedule.config) if item.schedule else {}),
            enabled=True,
        )
    elif renew is False and item.schedule is not None:
        # Pause keeps cron/config; deleting the row would lose renewal settings.
        item.schedule.enabled = False
    elif item.schedule is not None:
        if cron is not None:
            item.schedule.cron = cron
            item.schedule.next_run_at = next_run_after(cron, datetime.now(UTC))
        if config is not None:
            item.schedule.config = dict(config)
        if payload.enabled is not None:
            item.schedule.enabled = payload.enabled and item.enabled
    db.commit()
    return _reload(db, item.id)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_watchlist_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    user: AuthUser | None = Depends(require_login),
) -> None:
    item = _get(db, item_id)
    assert_client_access(db, user, item.client_id)
    schedule = item.schedule
    db.delete(item)
    if schedule is not None:
        db.delete(schedule)
    db.commit()


def _attach_schedule(
    db: Session,
    item: WatchlistItem,
    *,
    cron: str,
    config: dict[str, Any],
    enabled: bool,
) -> None:
    now = datetime.now(UTC)
    if item.schedule is None:
        schedule = AuditSchedule(
            client_id=item.client_id,
            url=item.url,
            cron=cron,
            enabled=enabled and item.enabled,
            config=dict(config or {}),
            next_run_at=next_run_after(cron, now),
        )
        db.add(schedule)
        db.flush()
        item.schedule_id = schedule.id
        item.schedule = schedule
    else:
        item.schedule.url = item.url
        item.schedule.cron = cron
        item.schedule.enabled = enabled and item.enabled
        item.schedule.config = dict(config or {})
        item.schedule.next_run_at = next_run_after(cron, now)


def _get(db: Session, item_id: UUID) -> WatchlistItem:
    item = db.scalar(
        select(WatchlistItem)
        .where(WatchlistItem.id == item_id)
        .options(selectinload(WatchlistItem.client), selectinload(WatchlistItem.schedule))
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Eintrag nicht gefunden.")
    return item


def _reload(db: Session, item_id: UUID) -> WatchlistRead:
    return _read(_get(db, item_id))


def _read(item: WatchlistItem) -> WatchlistRead:
    schedule = item.schedule
    return WatchlistRead(
        id=item.id,
        client_id=item.client_id,
        client_name=item.client.name if item.client else "",
        url=item.url,
        label=item.label,
        notes=item.notes,
        enabled=item.enabled,
        schedule_id=item.schedule_id,
        renew_enabled=bool(schedule and schedule.enabled),
        cron=schedule.cron if schedule else None,
        config=dict(schedule.config or {}) if schedule else {},
        last_audit_id=item.last_audit_id,
        last_overall_score=item.last_overall_score,
        last_checked_at=item.last_checked_at,
        next_run_at=schedule.next_run_at if schedule else None,
        created_at=item.created_at,
    )
