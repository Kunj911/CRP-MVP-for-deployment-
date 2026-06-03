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
    include=[
        "app.tasks.email_tasks",
        "app.tasks.order_tasks",
        "app.tasks.document_tasks",
        "app.tasks.scheduled_tasks",
        "app.tasks.notification_tasks",
    ],
)

from celery.signals import worker_process_init

@worker_process_init.connect
def init_worker(**kwargs):
    """
    Ensure SQLAlchemy engine connection pools are disposed of upon process fork,
    preventing concurrent query corruption in Celery workers.
    """
    from app.database.connection import engine
    engine.dispose()

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    task_default_queue="default",
    task_routes={
        "app.tasks.notification_tasks.*": {"queue": "notifications"},
        "app.tasks.email_tasks.*": {"queue": "emails"},
        "app.tasks.scheduled_tasks.*": {"queue": "scheduled"},
    },
)

# ── Celery Beat Schedule for Periodic Tasks ───────────────────────────────────
celery_app.conf.beat_schedule = {
    "daily-active-order-summary": {
        "task": "app.tasks.scheduled_tasks.send_daily_active_order_summary",
        "schedule": 86400.0,  # Daily (24 hours)
    },
    "weekly-order-summary": {
        "task": "app.tasks.scheduled_tasks.send_weekly_order_summary",
        "schedule": 604800.0,  # Weekly (7 days)
    },
    "pending-qa-review-reminders": {
        "task": "app.tasks.scheduled_tasks.send_pending_qa_review_reminders",
        "schedule": 3600.0,  # Hourly
    },
    "missing-required-documentation-warnings": {
        "task": "app.tasks.scheduled_tasks.send_missing_documentation_warnings",
        "schedule": 14400.0,  # Every 4 hours
    },
    "shipment-expected-dispatch-alerts": {
        "task": "app.tasks.scheduled_tasks.send_dispatch_alerts",
        "schedule": 7200.0,  # Every 2 hours
    },
}
