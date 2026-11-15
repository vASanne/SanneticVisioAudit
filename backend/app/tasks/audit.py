"""Celery task that executes one audit."""

from uuid import UUID

from app.services.audit_runner import execute_audit
from app.tasks.celery_app import celery_app


@celery_app.task(name="audits.run", soft_time_limit=1740, time_limit=1800)
def run_audit_task(audit_id: str) -> None:
    """Run the crawl, checks, and scoring for one stored audit."""

    execute_audit(UUID(audit_id))
