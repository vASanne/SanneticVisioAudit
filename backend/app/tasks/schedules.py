"""Periodic schedule runner."""

from __future__ import annotations

import structlog

from app.core.database import session_scope
from app.core.logging import setup_logging
from app.services.schedule_service import run_due_schedules
from app.tasks.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(name="schedules.tick")
def tick_schedules() -> int:
    """Enqueue due recurring audits."""

    setup_logging()
    with session_scope() as db:
        count = run_due_schedules(db)
    if count:
        logger.info("schedules_started", count=count)
    return count
