"""Celery application configuration using Redis as broker and result backend."""
from celery import Celery
from core.config import settings

celery_app = Celery(
    "redactai",
    broker=settings.REDIS_URL if settings.REDIS_URL else "memory://",
    backend=settings.REDIS_URL if settings.REDIS_URL else "cache+memory://",
    include=["core.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    task_always_eager=True,
    task_eager_propagates=True,
)
