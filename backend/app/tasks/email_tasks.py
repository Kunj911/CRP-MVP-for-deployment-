"""
app/tasks/email_tasks.py

General asynchronous tasks for sending template-based HTML emails.
"""

import logging
from typing import Any, Dict

from app.core.celery_app import celery_app
from app.services.email_service import send_template_email

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def send_template_email_task(
    self,
    to_address: str,
    subject: str,
    template_name: str,
    context: Dict[str, Any],
    fallback_text: str = ""
) -> bool:
    """
    Asynchronously renders an HTML email and dispatches it.
    """
    logger.info("Sending template email %s to %s", template_name, to_address)
    success = send_template_email(
        to_address=to_address,
        subject=subject,
        template_name=template_name,
        context=context,
        fallback_text=fallback_text
    )
    if not success:
        raise RuntimeError(f"Email delivery failed (adapter returned False) to {to_address}")
    return True
