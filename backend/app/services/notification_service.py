"""
app/services/notification_service.py

The notification engine for Live-Trace.

Architecture:
  - Event-driven: callers fire trigger functions (send_milestone_alert, etc.)
  - Each trigger resolves recipients, picks channels, renders the template,
    dispatches via channel adapters, and logs the result to the notifications table.
  - Retry logic: up to MAX_RETRIES attempts with exponential backoff.
  - Async-ready: dispatch is wrapped in a background thread so the API response
    is never blocked. Use fire_background() for fire-and-forget dispatch.

Trigger events:
  ┌─────────────────────────────────────┬──────────────────────────────────────┐
  │ Event                               │ Triggered by                         │
  ├─────────────────────────────────────┼──────────────────────────────────────┤
  │ MILESTONE_COMPLETED                 │ milestone_service.update_milestone_  │
  │                                     │ status() on COMPLETED transition      │
  ├─────────────────────────────────────┼──────────────────────────────────────┤
  │ DOCUMENT_UPLOADED                   │ upload_service.upload_document()     │
  ├─────────────────────────────────────┼──────────────────────────────────────┤
  │ SHIPMENT_DISPATCHED                 │ order_service.update_order_status()  │
  │                                     │ when status → SHIPMENT_DISPATCHED    │
  └─────────────────────────────────────┴──────────────────────────────────────┘

Channel routing:
  - User.notification_preference (future field) → or fall back to EMAIL
  - WhatsApp if user has phone_number set in their profile

Retry config:
  MAX_RETRIES = 3
  RETRY_DELAYS = [5s, 30s, 120s]   (exponential backoff)
"""

import logging
import threading
import time
from datetime import datetime, UTC
from typing import Optional

from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.order import Order
from app.models.user import User
from app.services.channels.email_channel import send_email
from app.services.channels.whatsapp_channel import send_whatsapp
from app.services import notification_templates as tmpl

logger = logging.getLogger(__name__)

# ── Retry configuration ───────────────────────────────────────────────────────
MAX_RETRIES   = 3
RETRY_DELAYS  = [5, 30, 120]   # seconds between each retry attempt


# ── Internal dispatch core ────────────────────────────────────────────────────

def _dispatch_email(
    notification: Notification,
    recipient: User,
    subject: str,
    body_text: str,
    body_html: str,
    db: Session,
) -> None:
    """
    Attempt email delivery with retry logic.
    Updates notification.delivery_status + sent_at in DB on success or exhaustion.
    """
    email = recipient.email
    if not email:
        logger.warning(
            "User %s has no email address — skipping EMAIL notification %s",
            recipient.id, notification.id,
        )
        _mark_failed(notification, db)
        return

    success = False
    for attempt in range(1, MAX_RETRIES + 1):
        logger.debug(
            "Email dispatch attempt %d/%d for notification_id=%s to %s",
            attempt, MAX_RETRIES, notification.id, email,
        )
        success = send_email(
            to_address=email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
        )
        if success:
            break

        if attempt < MAX_RETRIES:
            delay = RETRY_DELAYS[attempt - 1]
            logger.info(
                "Email attempt %d failed for notification_id=%s — retrying in %ds",
                attempt, notification.id, delay,
            )
            time.sleep(delay)

    if success:
        _mark_sent(notification, db)
    else:
        logger.error(
            "Email delivery FAILED after %d attempts for notification_id=%s (user_id=%s)",
            MAX_RETRIES, notification.id, recipient.id,
        )
        _mark_failed(notification, db)


def _dispatch_whatsapp(
    notification: Notification,
    recipient: User,
    message: str,
    db: Session,
) -> None:
    """
    Attempt WhatsApp delivery with retry logic.
    Requires recipient.phone_number to be set.
    """
    phone = getattr(recipient, "phone_number", None)
    if not phone:
        logger.warning(
            "User %s has no phone_number — skipping WHATSAPP notification %s",
            recipient.id, notification.id,
        )
        _mark_failed(notification, db)
        return

    success = False
    for attempt in range(1, MAX_RETRIES + 1):
        success = send_whatsapp(to_phone=phone, message=message)
        if success:
            break
        if attempt < MAX_RETRIES:
            delay = RETRY_DELAYS[attempt - 1]
            time.sleep(delay)

    if success:
        _mark_sent(notification, db)
    else:
        _mark_failed(notification, db)


def _mark_sent(notification: Notification, db: Session) -> None:
    notification.delivery_status = "SENT"
    notification.sent_at = datetime.now(UTC)
    try:
        db.commit()
    except Exception as exc:
        logger.error("Failed to commit SENT status for notification %s: %s", notification.id, exc)


def _mark_failed(notification: Notification, db: Session) -> None:
    notification.delivery_status = "FAILED"
    try:
        db.commit()
    except Exception as exc:
        logger.error("Failed to commit FAILED status for notification %s: %s", notification.id, exc)


def _create_notification_record(
    db: Session,
    order_id: int,
    user_id: int,
    channel: str,
    message: str,
) -> Notification:
    """Insert a PENDING notification record into the DB and return it."""
    record = Notification(
        order_id=order_id,
        user_id=user_id,
        notification_type=channel,
        message=message,
        delivery_status="PENDING",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def _get_order_customer_user(order: Order, db: Session) -> Optional[User]:
    """Return the customer-role user linked to the order's customer, if any."""
    if not order.customer_id:
        return None
    return (
        db.query(User)
        .filter(User.customer_id == order.customer_id, User.role == "CUSTOMER")
        .first()
    )


def _fire_background(fn, *args, **kwargs) -> None:
    """
    Queue task using Celery if enabled, else fallback to daemon threads.
    """
    from app.config.settings import get_settings
    settings = get_settings()

    if getattr(settings, "CELERY_ENABLED", False):
        try:
            if fn.__name__ == "_dispatch_email":
                notification, recipient, subject, body_text, body_html, _ = args
                from app.tasks.notification_tasks import dispatch_email_task
                dispatch_email_task.delay(
                    notification.id,
                    recipient.id,
                    subject,
                    body_text,
                    body_html,
                )
                logger.info("Queued email notification %d via Celery", notification.id)
                return
            elif fn.__name__ == "_dispatch_whatsapp":
                notification, recipient, message, _ = args
                from app.tasks.notification_tasks import dispatch_whatsapp_task
                dispatch_whatsapp_task.delay(
                    notification.id,
                    recipient.id,
                    message,
                )
                logger.info("Queued WhatsApp notification %d via Celery", notification.id)
                return
        except Exception as exc:
            logger.error("Failed to queue via Celery: %s. Falling back to daemon thread.", exc)

    t = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    t.start()


# ── Public trigger functions ──────────────────────────────────────────────────

def send_milestone_alert(
    order_id: int,
    milestone_stage: str,
    stage_label: str,
    completed_at: datetime,
    db: Session,
) -> None:
    """
    Trigger: milestone COMPLETED.
    Called by milestone_service.update_milestone_status().

    Recipients:
      - The CUSTOMER user linked to the order.
    Channels:
      - EMAIL  (always attempted if user has email)
      - WHATSAPP (attempted if user has phone_number and WhatsApp is configured)
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        logger.warning("send_milestone_alert: order_id=%s not found", order_id)
        return

    recipient = _get_order_customer_user(order, db)
    if not recipient:
        logger.info(
            "No CUSTOMER user for order_id=%s — skipping milestone notification", order_id
        )
        return

    customer_name = getattr(order.customer, "company_name", "Valued Customer") if order.customer else "Valued Customer"
    completed_str = completed_at.strftime("%Y-%m-%d %H:%M")

    # ── Email dispatch ─────────────────────────────────────────────────────
    email_tmpl = tmpl.milestone_completed_email(
        order_code=order.order_code,
        stage_label=stage_label,
        customer_name=customer_name,
        completed_at=completed_str,
    )
    email_record = _create_notification_record(
        db=db,
        order_id=order_id,
        user_id=recipient.id,
        channel="EMAIL",
        message=email_tmpl.body_text,
    )
    _fire_background(
        _dispatch_email,
        email_record, recipient,
        email_tmpl.subject, email_tmpl.body_text, email_tmpl.body_html,
        db,
    )

    # ── WhatsApp dispatch (if user has phone) ──────────────────────────────
    if getattr(recipient, "phone_number", None):
        wa_tmpl = tmpl.milestone_completed_whatsapp(
            order_code=order.order_code,
            stage_label=stage_label,
            completed_at=completed_str,
        )
        wa_record = _create_notification_record(
            db=db,
            order_id=order_id,
            user_id=recipient.id,
            channel="WHATSAPP",
            message=wa_tmpl.message,
        )
        _fire_background(_dispatch_whatsapp, wa_record, recipient, wa_tmpl.message, db)

    logger.info(
        "Milestone notification queued: order_id=%s stage=%s user_id=%s",
        order_id, milestone_stage, recipient.id,
    )


def send_document_uploaded_alert(
    order_id: int,
    document_type: str,
    file_name: str,
    uploaded_at: datetime,
    db: Session,
) -> None:
    """
    Trigger: document uploaded to vault.
    Called by upload_service.upload_document() after DB commit.

    Recipients: CUSTOMER user for the order.
    Channels:   EMAIL only (document alerts are lower urgency).
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return

    recipient = _get_order_customer_user(order, db)
    if not recipient:
        return

    customer_name = getattr(order.customer, "company_name", "Valued Customer") if order.customer else "Valued Customer"
    uploaded_str  = uploaded_at.strftime("%Y-%m-%d %H:%M")

    email_tmpl = tmpl.document_uploaded_email(
        order_code=order.order_code,
        document_type=document_type,
        file_name=file_name,
        customer_name=customer_name,
        uploaded_at=uploaded_str,
    )
    email_record = _create_notification_record(
        db=db,
        order_id=order_id,
        user_id=recipient.id,
        channel="EMAIL",
        message=email_tmpl.body_text,
    )
    _fire_background(
        _dispatch_email,
        email_record, recipient,
        email_tmpl.subject, email_tmpl.body_text, email_tmpl.body_html,
        db,
    )
    logger.info(
        "Document upload notification queued: order_id=%s doc_type=%s", order_id, document_type
    )


def send_shipment_dispatched_alert(
    order_id: int,
    dispatched_at: datetime,
    vessel_name: Optional[str] = None,
    bl_number: Optional[str] = None,
    db: Session = None,
) -> None:
    """
    Trigger: order status → SHIPMENT_DISPATCHED.
    Called by order_service.update_order_status().

    Recipients: CUSTOMER user for the order.
    Channels:   EMAIL + WhatsApp (highest urgency event).
    """
    if db is None:
        logger.error("send_shipment_dispatched_alert called with no db session")
        return

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return

    recipient = _get_order_customer_user(order, db)
    if not recipient:
        return

    customer_name  = getattr(order.customer, "company_name", "Valued Customer") if order.customer else "Valued Customer"
    dispatched_str = dispatched_at.strftime("%Y-%m-%d %H:%M")

    # Email
    email_tmpl = tmpl.shipment_dispatched_email(
        order_code=order.order_code,
        customer_name=customer_name,
        dispatched_at=dispatched_str,
        vessel_name=vessel_name,
        bl_number=bl_number,
    )
    email_record = _create_notification_record(
        db=db,
        order_id=order_id,
        user_id=recipient.id,
        channel="EMAIL",
        message=email_tmpl.body_text,
    )
    _fire_background(
        _dispatch_email,
        email_record, recipient,
        email_tmpl.subject, email_tmpl.body_text, email_tmpl.body_html,
        db,
    )

    # WhatsApp
    if getattr(recipient, "phone_number", None):
        wa_tmpl = tmpl.shipment_dispatched_whatsapp(
            order_code=order.order_code,
            dispatched_at=dispatched_str,
            vessel_name=vessel_name,
        )
        wa_record = _create_notification_record(
            db=db,
            order_id=order_id,
            user_id=recipient.id,
            channel="WHATSAPP",
            message=wa_tmpl.message,
        )
        _fire_background(_dispatch_whatsapp, wa_record, recipient, wa_tmpl.message, db)

    logger.info(
        "Shipment dispatch notification queued: order_id=%s user_id=%s", order_id, recipient.id
    )


# ── Notification listing (for API) ───────────────────────────────────────────

def get_notifications_for_user(
    user_id: int,
    db: Session,
    unread_only: bool = False,
    limit: int = 50,
) -> list[Notification]:
    """
    Return recent notifications for a user.
    unread_only=True filters to PENDING/FAILED (i.e. not yet acknowledged as SENT).
    """
    query = db.query(Notification).filter(Notification.user_id == user_id)
    if unread_only:
        query = query.filter(Notification.delivery_status != "SENT")
    return (
        query.order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )
