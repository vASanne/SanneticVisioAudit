"""Celery application. The broker is Redis; task results are not stored."""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()
celery_app = Celery("visioaudit", broker=settings.celery_broker_url)
celery_app.conf.update(
    include=["app.tasks.audit"],
    task_ignore_result=True,
    task_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)
