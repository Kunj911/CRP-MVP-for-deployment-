"""
app/tasks/notification_tasks.py

Celery tasks for asynchronous email notification delivery.
"""

import logging
from datetime import UTC, datetime
from typing import Optional

from app.core.celery_app import celery_app
from app.database.connection import SessionLocal
from app.models.notification import Notification
from app.services.channels.email_channel import send_email

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def dispatch_email_task(
    self,
    notification_id: Optional[int],
    to_address: str,
    subject: str,
    body_text: str,
    body_html: str,
) -> None:
    """
    Send one email. If notification_id is provided, update delivery status.
    """
    logger.info("Executing email task notification_id=%s to=%s", notification_id, to_address)

    db = SessionLocal()
    notification = None
    try:
        if notification_id is not None:
            notification = db.query(Notification).filter(Notification.id == notification_id).first()
            if not notification:
                logger.error("Email task failed: notification_id=%s not found", notification_id)
                return

        success = send_email(
            to_address=to_address,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
        )

        if not success:
            raise RuntimeError("Email provider did not accept message")

        if notification:
            notification.delivery_status = "SENT"
            notification.sent_at = datetime.now(UTC)
            db.commit()

        logger.info("Email sent successfully notification_id=%s to=%s", notification_id, to_address)
    except Exception as exc:
        db.rollback()
        if self.request.retries >= self.max_retries:
            logger.error(
                "Email delivery exhausted retries notification_id=%s to=%s error=%s",
                notification_id,
                to_address,
                exc,
            )
            if notification_id is not None:
                notification = db.query(Notification).filter(Notification.id == notification_id).first()
                if notification:
                    notification.delivery_status = "FAILED"
                    db.commit()
        raise
    finally:
        db.close()
