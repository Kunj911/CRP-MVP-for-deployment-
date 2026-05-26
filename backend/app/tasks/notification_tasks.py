"""
app/tasks/notification_tasks.py

Celery tasks for asynchronous notification delivery with retry strategy.
"""

import logging
from datetime import datetime, UTC
from app.core.celery_app import celery_app
from app.database.connection import SessionLocal
from app.models.notification import Notification
from app.models.user import User
from app.services.channels.email_channel import send_email
from app.services.channels.whatsapp_channel import send_whatsapp

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def dispatch_email_task(
    self,
    notification_id: int,
    recipient_id: int,
    subject: str,
    body_text: str,
    body_html: str,
):
    """
    Celery task to send an email. Updates notification status.
    """
    logger.info("Executing Celery email task for notification_id=%d", notification_id)
    db = SessionLocal()
    try:
        notification = db.query(Notification).filter(Notification.id == notification_id).first()
        recipient = db.query(User).filter(User.id == recipient_id).first()
        
        if not notification or not recipient:
            logger.error("Email task failed: notification_id=%d or user_id=%d not found", notification_id, recipient_id)
            return

        success = send_email(
            to_address=recipient.email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
        )

        if success:
            notification.delivery_status = "SENT"
            notification.sent_at = datetime.now(UTC)
            db.commit()
            logger.info("Email sent successfully for notification_id=%d", notification_id)
        else:
            logger.warning("Email attempt failed for notification_id=%d, retrying...", notification_id)
            raise self.retry(exc=Exception("SMTP delivery failed"))

    except Exception as exc:
        db.rollback()
        # If we failed and have exhausted retries, mark as FAILED
        if self.request.retries >= self.max_retries:
            logger.error("Email delivery exhausted all retries for notification_id=%d. Error: %s", notification_id, exc)
            notification = db.query(Notification).filter(Notification.id == notification_id).first()
            if notification:
                notification.delivery_status = "FAILED"
                db.commit()
        else:
            raise exc
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def dispatch_whatsapp_task(
    self,
    notification_id: int,
    recipient_id: int,
    message: str,
):
    """
    Celery task to send a WhatsApp notification. Updates notification status.
    """
    logger.info("Executing Celery WhatsApp task for notification_id=%d", notification_id)
    db = SessionLocal()
    try:
        notification = db.query(Notification).filter(Notification.id == notification_id).first()
        recipient = db.query(User).filter(User.id == recipient_id).first()
        
        if not notification or not recipient:
            logger.error("WhatsApp task failed: notification_id=%d or user_id=%d not found", notification_id, recipient_id)
            return

        phone = getattr(recipient, "phone_number", None)
        if not phone:
            logger.warning("WhatsApp task skipped: user_id=%d has no phone number", recipient_id)
            notification.delivery_status = "FAILED"
            db.commit()
            return

        success = send_whatsapp(to_phone=phone, message=message)

        if success:
            notification.delivery_status = "SENT"
            notification.sent_at = datetime.now(UTC)
            db.commit()
            logger.info("WhatsApp sent successfully for notification_id=%d", notification_id)
        else:
            logger.warning("WhatsApp attempt failed for notification_id=%d, retrying...", notification_id)
            raise self.retry(exc=Exception("WhatsApp API delivery failed"))

    except Exception as exc:
        db.rollback()
        # If we failed and have exhausted retries, mark as FAILED
        if self.request.retries >= self.max_retries:
            logger.error("WhatsApp delivery exhausted all retries for notification_id=%d. Error: %s", notification_id, exc)
            notification = db.query(Notification).filter(Notification.id == notification_id).first()
            if notification:
                notification.delivery_status = "FAILED"
                db.commit()
        else:
            raise exc
    finally:
        db.close()
