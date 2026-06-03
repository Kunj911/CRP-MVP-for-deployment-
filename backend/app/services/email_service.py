"""
app/services/email_service.py

Email service layer responsible for loading, rendering Jinja2 templates, and
passing the rendered output to the configured email channel adapter.
"""

import os
import logging
from typing import Any, Dict, Optional, List

from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.services.channels.email_channel import send_email as send_via_channel

logger = logging.getLogger(__name__)

# Calculate absolute path to the templates/emails folder
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "../../templates/emails"))

# Ensure directory exists
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# Initialize Jinja2 environment
jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"])
)


def send_email(to_address: str, subject: str, body_text: str) -> bool:
    """Send a plain text email."""
    return send_via_channel(
        to_address=to_address,
        subject=subject,
        body_text=body_text,
        body_html=None
    )


def send_html_email(to_address: str, subject: str, body_html: str, body_text: Optional[str] = None) -> bool:
    """Send an HTML email with optional plain text fallback."""
    return send_via_channel(
        to_address=to_address,
        subject=subject,
        body_text=body_text or subject,
        body_html=body_html
    )


def send_template_email(
    to_address: str,
    subject: str,
    template_name: str,
    context: Dict[str, Any],
    fallback_text: str = ""
) -> bool:
    """
    Renders an HTML email from a template and sends it asynchronously/via channel.
    """
    try:
        template = jinja_env.get_template(template_name)
        body_html = template.render(**context)
        return send_via_channel(
            to_address=to_address,
            subject=subject,
            body_text=fallback_text or subject,
            body_html=body_html
        )
    except Exception as e:
        logger.error("Error rendering/sending email template %s: %s", template_name, e)
        # Fallback to simple text delivery if template render fails
        return send_via_channel(
            to_address=to_address,
            subject=subject,
            body_text=fallback_text or subject,
            body_html=None
        )


def send_bulk_email(
    to_addresses: List[str],
    subject: str,
    template_name: str,
    context: Dict[str, Any],
    fallback_text: str = ""
) -> Dict[str, bool]:
    """
    Sends the same template email to multiple recipients, returning a dict of recipient -> success status.
    """
    results = {}
    for addr in to_addresses:
        results[addr] = send_template_email(
            to_address=addr,
            subject=subject,
            template_name=template_name,
            context=context,
            fallback_text=fallback_text
        )
    return results
