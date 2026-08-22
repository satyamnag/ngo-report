"""Celery application (Redis broker + result backend)."""

from celery import Celery

from .config import settings

celery_app = Celery(
    "ngo_report",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    result_expires=3600,
    timezone="UTC",
    enable_utc=True,
)

celery_app.autodiscover_tasks(["app"])

# Explicit import so tasks are registered even before worker finalize.
from . import tasks  # noqa: E402,F401