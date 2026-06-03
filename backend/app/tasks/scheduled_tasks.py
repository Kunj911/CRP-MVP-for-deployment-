"""
app/tasks/scheduled_tasks.py

Periodic background tasks executed by Celery Beat for reporting and warning alerts.
"""

import logging
from datetime import timedelta, date

from app.core.celery_app import celery_app
from app.database.connection import SessionLocal
from app.models.order import Order
from app.models.document import Document
from app.models.order_document_requirement import OrderDocumentRequirement
from app.models.user import User
from app.services.channels.email_channel import send_email

logger = logging.getLogger(__name__)


@celery_app.task
def send_daily_active_order_summary() -> None:
    """
    Summarizes current active orders and progress, emailing Admin users daily.
    """
    logger.info("Executing periodic daily active order summary task")
    db = SessionLocal()
    try:
        active_orders = db.query(Order).filter(
            Order.shipment_status.notin_(["DELIVERED", "CANCELLED"])
        ).all()
        
        if not active_orders:
            logger.info("No active orders found for summary.")
            return

        admin_users = db.query(User).filter(
            User.role.in_(["ADMIN", "SUPER_ADMIN"]),
            User.is_active == True
        ).all()

        if not admin_users:
            return

        summary = "Daily Active Order Summary:\n\n"
        for o in active_orders:
            summary += f"- Order {o.order_code}: {o.product_name} (Status: {o.shipment_status})\n"
            
        for admin in admin_users:
            send_email(
                to_address=admin.email,
                subject="Daily Operations Active Order Summary",
                body_text=summary
            )
    except Exception as exc:
        logger.error("Error in send_daily_active_order_summary: %s", exc)
    finally:
        db.close()


@celery_app.task
def send_weekly_order_summary() -> None:
    """
    Weekly summary report on total and completed orders.
    """
    logger.info("Executing periodic weekly order summary task")
    db = SessionLocal()
    try:
        total_orders = db.query(Order).count()
        delivered_orders = db.query(Order).filter(Order.shipment_status == "DELIVERED").count()
        
        admin_users = db.query(User).filter(
            User.role.in_(["ADMIN", "SUPER_ADMIN"]),
            User.is_active == True
        ).all()

        summary = f"Weekly Operations Summary:\n\nTotal Orders in System: {total_orders}\nDelivered Orders: {delivered_orders}\n"
        
        for admin in admin_users:
            send_email(
                to_address=admin.email,
                subject="Weekly Operations Summary Report",
                body_text=summary
            )
    except Exception as exc:
        logger.error("Error in send_weekly_order_summary: %s", exc)
    finally:
        db.close()


@celery_app.task
def send_pending_qa_review_reminders() -> None:
    """
    Checks for documents pending QA review and logs alerts.
    """
    logger.info("Executing periodic pending QA review reminders task")
    db = SessionLocal()
    try:
        pending_docs = db.query(Document).filter(
            Document.status.in_(["under_review", "uploaded"]),
            Document.is_deleted == False
        ).all()
        
        if not pending_docs:
            logger.info("No pending QA documents found.")
            return

        qa_users = db.query(User).filter(
            User.role.in_(["QA", "ADMIN", "SUPER_ADMIN"]),
            User.is_active == True
        ).all()

        if not qa_users:
            return

        body = "Daily Pending QA Reviews Reminder:\n\nThe following documents are waiting for review:\n\n"
        for doc in pending_docs:
            order_code = doc.order.order_code if doc.order else "Unknown Order"
            body += f"- Order {order_code}: {doc.document_type} (Uploaded: {doc.uploaded_at})\n"

        for qa in qa_users:
            send_email(
                to_address=qa.email,
                subject="Pending QA Document Review Reminder",
                body_text=body
            )
    except Exception as exc:
        logger.error("Error in send_pending_qa_review_reminders: %s", exc)
    finally:
        db.close()


@celery_app.task
def send_missing_documentation_warnings() -> None:
    """
    Warns the documentation team of active orders missing required documentation.
    """
    logger.info("Executing periodic missing documentation warnings task")
    db = SessionLocal()
    try:
        missing_reqs = db.query(OrderDocumentRequirement).filter(
            OrderDocumentRequirement.required == True,
            OrderDocumentRequirement.uploaded == False
        ).all()

        if not missing_reqs:
            logger.info("No missing required documentation found.")
            return

        docs_staff = db.query(User).filter(
            User.role.in_(["DOCUMENTATION", "ADMIN", "SUPER_ADMIN"]),
            User.is_active == True
        ).all()

        if not docs_staff:
            return

        body = "Missing Required Documentation Warnings:\n\n"
        for req in missing_reqs:
            order_code = req.order.order_code if req.order else "Unknown Order"
            body += f"- Order {order_code}: Missing required '{req.document_type}'\n"

        for staff in docs_staff:
            send_email(
                to_address=staff.email,
                subject="Alert: Missing Required Export Documentation",
                body_text=body
            )
    except Exception as exc:
        logger.error("Error in send_missing_documentation_warnings: %s", exc)
    finally:
        db.close()


@celery_app.task
def send_dispatch_alerts() -> None:
    """
    Warns 48 hours prior to expected dispatch if documentation is incomplete.
    """
    logger.info("Executing periodic expected dispatch alerts task")
    db = SessionLocal()
    try:
        cutoff = date.today() + timedelta(days=2)
        upcoming_orders = db.query(Order).filter(
            Order.expected_dispatch_date <= cutoff,
            Order.shipment_status.notin_(["SHIPPED", "DELIVERED", "CANCELLED"])
        ).all()

        if not upcoming_orders:
            logger.info("No upcoming dispatch orders found.")
            return

        ops_staff = db.query(User).filter(
            User.role.in_(["ADMIN", "SUPER_ADMIN", "DOCUMENTATION"]),
            User.is_active == True
        ).all()

        if not ops_staff:
            return

        alert_body = "Alert: Upcoming Dispatches within 48 Hours check:\n\n"
        has_alerts = False
        
        for order in upcoming_orders:
            unapproved = db.query(OrderDocumentRequirement).filter(
                OrderDocumentRequirement.order_id == order.id,
                OrderDocumentRequirement.required == True,
                OrderDocumentRequirement.approved == False
            ).all()

            if unapproved:
                has_alerts = True
                missing_types = ", ".join([r.document_type for r in unapproved])
                alert_body += f"- Order {order.order_code} (Expected Dispatch: {order.expected_dispatch_date}) lacks approved: {missing_types}\n"

        if has_alerts:
            for staff in ops_staff:
                send_email(
                    to_address=staff.email,
                    subject="CRITICAL: Upcoming Dispatch Documentation Alert",
                    body_text=alert_body
                )
    except Exception as exc:
        logger.error("Error in send_dispatch_alerts: %s", exc)
    finally:
        db.close()
