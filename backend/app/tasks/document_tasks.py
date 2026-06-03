"""
app/tasks/document_tasks.py

Asynchronous Celery tasks for document review and upload email notifications.
"""

import logging
from app.core.celery_app import celery_app
from app.database.connection import SessionLocal
from app.models.order import Order
from app.models.document import Document
from app.models.user import User
from app.services.email_service import send_template_email
from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def get_doc_label(doc_type: str) -> str:
    """Helper to convert raw document type string to human-readable label."""
    return doc_type.replace("_", " ").title()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def send_document_uploaded_email(self, order_id: int, document_id: int) -> None:
    """
    Notify QA and Admins that a new document has been uploaded and is pending review.
    """
    logger.info("Executing send_document_uploaded_email for document_id=%d", document_id)
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not order or not doc:
            logger.error("Order %d or Document %d not found", order_id, document_id)
            return

        # Query active QA and Admin reviewers
        reviewers = db.query(User).filter(
            User.role.in_(["QA", "ADMIN", "SUPER_ADMIN"]),
            User.is_active == True
        ).all()

        uploader_name = doc.uploader.full_name if doc.uploader else "System/Vendor"

        for reviewer in reviewers:
            context = {
                "reviewer_name": reviewer.full_name,
                "order_code": order.order_code,
                "document_type_label": get_doc_label(doc.document_type),
                "file_name": doc.file_name or "Uploaded File",
                "uploaded_by_name": uploader_name,
                "review_url": f"{settings.FRONTEND_APP_URL}/orders/{order.id}"
            }
            ok = send_template_email(
                to_address=reviewer.email,
                subject=f"Document Pending Review: {order.order_code} - {get_doc_label(doc.document_type)}",
                template_name="document_uploaded.html",
                context=context,
                fallback_text=f"A new document ({get_doc_label(doc.document_type)}) has been uploaded for order {order.order_code} and is pending review."
            )
            if not ok:
                raise RuntimeError(f"Email delivery failed to {reviewer.email}")
    finally:
        db.close()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def send_document_approved_email(self, order_id: int, document_id: int) -> None:
    """
    Notify customer contacts that an uploaded document checklist item was approved.
    """
    logger.info("Executing send_document_approved_email for document_id=%d", document_id)
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not order or not doc:
            logger.error("Order %d or Document %d not found", order_id, document_id)
            return

        # Query active customer contacts
        customer_users = db.query(User).filter(
            User.customer_id == order.customer_id,
            User.role == "CUSTOMER",
            User.is_active == True
        ).all()

        for user in customer_users:
            context = {
                "customer_name": user.full_name,
                "order_code": order.order_code,
                "document_type_label": get_doc_label(doc.document_type),
                "file_name": doc.file_name or "Approved File",
                "approved_at": str(doc.reviewed_at) if doc.reviewed_at else "Recently",
                "vault_url": f"{settings.FRONTEND_APP_URL}/documents"
            }
            ok = send_template_email(
                to_address=user.email,
                subject=f"Document Approved: {order.order_code} - {get_doc_label(doc.document_type)}",
                template_name="document_approved.html",
                context=context,
                fallback_text=f"The document {get_doc_label(doc.document_type)} for order {order.order_code} has been approved."
            )
            if not ok:
                raise RuntimeError(f"Email delivery failed to {user.email}")
    finally:
        db.close()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def send_document_rejected_email(self, order_id: int, document_id: int, remarks: str) -> None:
    """
    Notify customer and uploader that an uploaded document checklist item was rejected.
    """
    logger.info("Executing send_document_rejected_email for document_id=%d", document_id)
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not order or not doc:
            logger.error("Order %d or Document %d not found", order_id, document_id)
            return

        # Notify customer contacts and the uploader
        recipients = set()
        customer_users = db.query(User).filter(
            User.customer_id == order.customer_id,
            User.role == "CUSTOMER",
            User.is_active == True
        ).all()
        for u in customer_users:
            recipients.add(u.email)
            
        if doc.uploader and doc.uploader.is_active:
            recipients.add(doc.uploader.email)

        for email in recipients:
            context = {
                "order_code": order.order_code,
                "document_type_label": get_doc_label(doc.document_type),
                "file_name": doc.file_name or "Rejected File",
                "remarks": remarks,
                "upload_url": f"{settings.FRONTEND_APP_URL}/orders/{order.id}"
            }
            ok = send_template_email(
                to_address=email,
                subject=f"Action Required: Document Rejected for {order.order_code} - {get_doc_label(doc.document_type)}",
                template_name="document_rejected.html",
                context=context,
                fallback_text=f"The document {get_doc_label(doc.document_type)} for order {order.order_code} was rejected. Reason: {remarks}"
            )
            if not ok:
                raise RuntimeError(f"Email delivery failed to {email}")
    finally:
        db.close()
