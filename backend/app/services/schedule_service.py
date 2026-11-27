"""Cron helpers and due-schedule runner."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.schemas import AuditCreate
from app.models import AuditSchedule
from app.services.audit_service import QueueUnavailableError, create_audit

logger = structlog.get_logger()


def next_run_after(cron: str, moment: datetime) -> datetime:
    """Next UTC run for a daily fixed hour/minute cron (``M H * * *``)."""

    minute, hour = _daily_hour_minute(cron)
    base = moment.astimezone(UTC)
    candidate = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= base:
        candidate = candidate + timedelta(days=1)
    return candidate


def _daily_hour_minute(cron: str) -> tuple[int, int]:
    parts = cron.split()
    if len(parts) not in {5, 6}:
        raise ValueError("cron needs five fields, e.g. 0 6 * * *")
    minute, hour, *_ = parts
    if not minute.isdigit() or not hour.isdigit():
        raise ValueError("nur feste Stunde/Minute werden unterstützt, z. B. 0 6 * * *")
    target_minute = int(minute)
    target_hour = int(hour)
    if not 0 <= target_minute <= 59 or not 0 <= target_hour <= 23:
        raise ValueError("cron Stunde/Minute außerhalb des gültigen Bereichs")
    return target_minute, target_hour


def run_due_schedules(db: Session, *, now: datetime | None = None) -> int:
    """Enqueue audits for every enabled schedule that is due. Returns the count."""

    moment = now or datetime.now(UTC)
    rows = db.scalars(
        select(AuditSchedule).where(AuditSchedule.enabled.is_(True)).options(selectinload(AuditSchedule.client))
    ).all()
    started = 0
    for schedule in rows:
        due = schedule.next_run_at
        if due is not None and due > moment:
            continue
        config = dict(schedule.config or {})
        try:
            max_pages = int(config.get("max_pages", 25))
        except (TypeError, ValueError):
            max_pages = 25
        payload = AuditCreate(
            url=schedule.url,
            client_name=schedule.client.name,
            client_id=schedule.client_id,
            max_pages=max(1, min(max_pages, 500)),
            follow_links=config.get("follow_links", True) is not False,
            render_js=config.get("render_js", False) is True,
            probe_internal_links=config.get("probe_internal_links", True) is not False,
            llm_summary=config.get("llm_summary", False) is True,
        )
        try:
            create_audit(db, payload)
            schedule.last_run_at = moment
            schedule.next_run_at = next_run_after(schedule.cron, moment)
            db.commit()
            started += 1
        except QueueUnavailableError:
            db.rollback()
            logger.warning("schedule_queue_unavailable", schedule_id=str(schedule.id))
        except Exception:
            db.rollback()
            logger.exception("schedule_start_failed", schedule_id=str(schedule.id))
    return started
