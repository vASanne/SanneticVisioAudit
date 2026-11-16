"""Recurring audit schedules."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import AuthUser, allowed_client_ids, assert_client_access, require_login
from app.api.schemas import ScheduleCreate, ScheduleRead, ScheduleUpdate
from app.core.database import get_db
from app.crawler.errors import UnsafeUrlError
from app.crawler.safety import assert_public_url
from app.crawler.urls import normalize_start_url
from app.models import AuditSchedule, Client
from app.services.schedule_service import next_run_after

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("", response_model=list[ScheduleRead])
def list_schedules(
    db: Session = Depends(get_db),
    user: AuthUser | None = Depends(require_login),
) -> list[ScheduleRead]:
    query = select(AuditSchedule).options(selectinload(AuditSchedule.client)).order_by(AuditSchedule.created_at.desc())
    allowed = allowed_client_ids(db, user)
    if allowed is not None:
        if not allowed:
            return []
        query = query.where(AuditSchedule.client_id.in_(allowed))
    return [_read(row) for row in db.scalars(query).all()]


@router.post("", response_model=ScheduleRead, status_code=status.HTTP_201_CREATED)
def create_schedule(
    payload: ScheduleCreate,
    db: Session = Depends(get_db),
    user: AuthUser | None = Depends(require_login),
) -> ScheduleRead:
    assert_client_access(db, user, payload.client_id)
    client = db.get(Client, payload.client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mandant nicht gefunden.")
    try:
        url = normalize_start_url(payload.url)
        assert_public_url(url)
        now = datetime.now(timezone.utc)
        next_run = next_run_after(payload.cron, now)
    except UnsafeUrlError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    schedule = AuditSchedule(
        client_id=payload.client_id,
        url=url,
        cron=payload.cron,
        enabled=payload.enabled,
        config=dict(payload.config or {}),
        next_run_at=next_run,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    schedule.client = client
    return _read(schedule)


@router.get("/{schedule_id}", response_model=ScheduleRead)
def get_schedule(
    schedule_id: UUID,
    db: Session = Depends(get_db),
    user: AuthUser | None = Depends(require_login),
) -> ScheduleRead:
    schedule = _get(db, schedule_id)
    assert_client_access(db, user, schedule.client_id)
    return _read(schedule)


@router.patch("/{schedule_id}", response_model=ScheduleRead)
def update_schedule(
    schedule_id: UUID,
    payload: ScheduleUpdate,
    db: Session = Depends(get_db),
    user: AuthUser | None = Depends(require_login),
) -> ScheduleRead:
    schedule = _get(db, schedule_id)
    assert_client_access(db, user, schedule.client_id)
    try:
        if payload.url is not None:
            url = normalize_start_url(payload.url)
            assert_public_url(url)
            schedule.url = url
        if payload.cron is not None:
            schedule.cron = payload.cron
            schedule.next_run_at = next_run_after(payload.cron, datetime.now(timezone.utc))
        if payload.enabled is not None:
            schedule.enabled = payload.enabled
        if payload.config is not None:
            schedule.config = dict(payload.config)
    except UnsafeUrlError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    db.refresh(schedule)
    return _read(schedule)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: UUID,
    db: Session = Depends(get_db),
    user: AuthUser | None = Depends(require_login),
) -> None:
    schedule = _get(db, schedule_id)
    assert_client_access(db, user, schedule.client_id)
    db.delete(schedule)
    db.commit()


def _get(db: Session, schedule_id: UUID) -> AuditSchedule:
    schedule = db.scalar(
        select(AuditSchedule).where(AuditSchedule.id == schedule_id).options(selectinload(AuditSchedule.client))
    )
    if schedule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zeitplan nicht gefunden.")
    return schedule


def _read(schedule: AuditSchedule) -> ScheduleRead:
    return ScheduleRead(
        id=schedule.id,
        client_id=schedule.client_id,
        client_name=schedule.client.name if schedule.client else "",
        url=schedule.url,
        cron=schedule.cron,
        enabled=schedule.enabled,
        config=dict(schedule.config or {}),
        last_run_at=schedule.last_run_at,
        next_run_at=schedule.next_run_at,
        created_at=schedule.created_at,
    )
