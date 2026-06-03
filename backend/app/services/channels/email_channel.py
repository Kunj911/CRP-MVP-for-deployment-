"""
app/services/channels/email_channel.py

Email notification channel adapter.

The public send_email() interface is intentionally small so the rest of the
application can queue email work without caring which provider is used.

Default provider: Resend
Fallback providers: SMTP, SendGrid
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def send_email(
    to_address: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
) -> bool:
    """
    Send an email via the configured provider.

    Returns True when the provider accepts the message, otherwise False.
    Celery tasks own retries and failure tracking.
    """
    if not settings.EMAIL_ENABLED:
        logger.info("Email disabled - skipping send to %s", to_address)
        return False

    provider = settings.EMAIL_PROVIDER.lower()

    if provider == "resend":
        return _send_via_resend(to_address, subject, body_text, body_html)

    if provider == "sendgrid":
        return _send_via_sendgrid(to_address, subject, body_text, body_html)

    return _send_via_smtp(to_address, subject, body_text, body_html)


def _send_via_resend(
    to_address: str,
    subject: str,
    body_text: str,
    body_html: Optional[str],
) -> bool:
    """Send using Resend's HTTPS API."""
    try:
        import httpx
    except ImportError:
        logger.error("httpx package is required for Resend email delivery")
        return False

    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set - skipping email to %s", to_address)
        return False

    payload = {
        "from": settings.EMAIL_FROM,
        "to": [to_address],
        "subject": subject,
        "text": body_text,
    }
    if body_html:
        payload["html"] = body_html

    try:
        response = httpx.post(
            settings.RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )
    except httpx.HTTPError as exc:
        logger.error("Resend HTTP error sending email to %s: %s", to_address, exc)
        return False

    if response.status_code in (200, 201, 202):
        logger.info("Email accepted by Resend for %s | subject=%s", to_address, subject)
        return True

    logger.error(
        "Resend email failed for %s | status=%s | body=%s",
        to_address,
        response.status_code,
        response.text[:500],
    )
    return False


def _send_via_smtp(
    to_address: str,
    subject: str,
    body_text: str,
    body_html: Optional[str],
) -> bool:
    """Send using stdlib smtplib."""
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        logger.warning(
            "SMTP email not configured - skipping send to %s. "
            "Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD in .env",
            to_address,
        )
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to_address

    msg.attach(MIMEText(body_text, "plain"))
    if body_html:
        msg.attach(MIMEText(body_html, "html"))

    try:
        port = int(getattr(settings, "SMTP_PORT", 587))
        use_tls = getattr(settings, "SMTP_TLS", True)

        with smtplib.SMTP(settings.SMTP_HOST, port, timeout=15) as server:
            if use_tls:
                import ssl
                context = ssl.create_default_context()
                server.starttls(context=context)
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, to_address, msg.as_string())

        logger.info("Email sent via SMTP to %s | subject=%s", to_address, subject)
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed - check SMTP_USER / SMTP_PASSWORD")
        return False
    except smtplib.SMTPException as exc:
        logger.error("SMTP error sending email to %s: %s", to_address, exc)
        return False
    except Exception as exc:
        logger.error("Unexpected SMTP error sending email to %s: %s", to_address, exc)
        return False


def _send_via_sendgrid(
    to_address: str,
    subject: str,
    body_text: str,
    body_html: Optional[str],
) -> bool:
    """Send via SendGrid API when the optional sendgrid package is installed."""
    try:
        from sendgrid import SendGridAPIClient  # type: ignore
        from sendgrid.helpers.mail import Content, Mail, To  # type: ignore

        sg_api_key = getattr(settings, "SENDGRID_API_KEY", "")
        if not sg_api_key:
            logger.error("SENDGRID_API_KEY not set in .env")
            return False

        message = Mail(
            from_email=settings.EMAIL_FROM,
            to_emails=To(to_address),
            subject=subject,
            plain_text_content=Content("text/plain", body_text),
        )
        if body_html:
            message.add_content(Content("text/html", body_html))

        response = SendGridAPIClient(sg_api_key).send(message)
        if response.status_code in (200, 201, 202):
            logger.info("Email accepted by SendGrid for %s | status=%s", to_address, response.status_code)
            return True

        logger.error("SendGrid returned status %s for %s", response.status_code, to_address)
        return False
    except ImportError:
        logger.error("sendgrid package is not installed")
        return False
    except Exception as exc:
        logger.error("SendGrid error sending email to %s: %s", to_address, exc)
        return False
