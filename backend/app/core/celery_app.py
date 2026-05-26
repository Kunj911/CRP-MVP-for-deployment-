"""
app/core/celery_app.py

Celery application initialization.
Connects Celery tasks to the Redis broker and results backend.
"""

from celery import Celery
from app.config.settings import get_settings

settings = get_settings()

celery_app = Celery(
    "livetrace",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.notification_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)
