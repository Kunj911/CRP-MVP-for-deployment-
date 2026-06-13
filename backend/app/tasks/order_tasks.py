"""
app/tasks/order_tasks.py

Asynchronous Celery tasks for order lifecycle email notifications.
"""

import logging
from app.core.celery_app import celery_app
from app.database.connection import SessionLocal
from app.models.order import Order
from app.models.user import User
from app.services.email_service import send_template_email
from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def send_order_delivered_email(self, order_id: int) -> None:
    """
    Notify customer contacts that their order has been delivered.
    """
    logger.info("Executing send_order_delivered_email for order_id=%d", order_id)
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            logger.error("Order %d not found for order_delivered email task", order_id)
            return

        customer_users = db.query(User).filter(
            User.customer_id == order.customer_id,
            User.role == "CUSTOMER",
            User.is_active == True
        ).all()

        for user in customer_users:
            context = {
                "user_name": user.full_name,
                "customer_name": order.customer.company_name if order.customer else "Valued Customer",
                "order_code": order.order_code,
                "product_name": order.product_name,
                "quantity": float(order.quantity) if order.quantity else 0.0,
                "unit": order.unit or "",
                "vault_url": f"{settings.FRONTEND_APP_URL}/documents"
            }
            ok = send_template_email(
                to_address=user.email,
                subject=f"Shipment Delivered: {order.order_code}",
                template_name="order_delivered.html",
                context=context,
                fallback_text=f"Your order {order.order_code} has been delivered successfully."
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
def send_shipment_dispatched_email(self, order_id: int) -> None:
    """
    Notify customer contacts that their shipment has been dispatched.
    """
    logger.info("Executing send_shipment_dispatched_email for order_id=%d", order_id)
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            logger.error("Order %d not found for shipment_dispatched email task", order_id)
            return

        customer_users = db.query(User).filter(
            User.customer_id == order.customer_id,
            User.role == "CUSTOMER",
            User.is_active == True
        ).all()

        for user in customer_users:
            context = {
                "user_name": user.full_name,
                "customer_name": order.customer.company_name if order.customer else "Valued Customer",
                "order_code": order.order_code,
                "product_name": order.product_name,
                "quantity": float(order.quantity) if order.quantity else 0.0,
                "unit": order.unit or "",
                "expected_delivery_date": str(order.expected_delivery_date) if order.expected_delivery_date else "TBD",
                "order_url": f"{settings.FRONTEND_APP_URL}/orders/{order.id}"
            }
            ok = send_template_email(
                to_address=user.email,
                subject=f"Shipment Dispatched: {order.order_code}",
                template_name="shipment_dispatched.html",
                context=context,
                fallback_text=f"Your shipment for order {order.order_code} has been dispatched."
            )
            if not ok:
                raise RuntimeError(f"Email delivery failed to {user.email}")
    finally:
        db.close()
