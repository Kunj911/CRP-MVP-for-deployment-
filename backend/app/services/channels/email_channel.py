"""
app/services/channels/email_channel.py

Email notification channel adapter.

Architecture:
  - Uses SMTP for development (settings.SMTP_* vars)
  - Designed to swap to SendGrid / AWS SES by swapping _send_via_smtp()
    with _send_via_sendgrid() — interface stays identical

Configuration (.env):
  EMAIL_FROM=noreply@live-trace.com
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USER=your@email.com
  SMTP_PASSWORD=your_app_password
  SMTP_TLS=true

  To use SendGrid instead:
    NOTIFICATION_EMAIL_PROVIDER=sendgrid
    SENDGRID_API_KEY=SG.xxx
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
    Send an email via SMTP (dev) or configured provider (prod).

    Returns:
        True  — message accepted by server
        False — delivery failed (caller logs + marks FAILED in DB)
    """
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        logger.warning(
            "Email not configured — skipping send to %s. "
            "Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD in .env",
            to_address,
        )
        return False

    provider = getattr(settings, "NOTIFICATION_EMAIL_PROVIDER", "smtp").lower()

    if provider == "sendgrid":
        return _send_via_sendgrid(to_address, subject, body_text, body_html)

    return _send_via_smtp(to_address, subject, body_text, body_html)


def _send_via_smtp(
    to_address: str,
    subject: str,
    body_text: str,
    body_html: Optional[str],
) -> bool:
    """Send using stdlib smtplib — works with Gmail, Outlook, Mailgun SMTP."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to_address

    msg.attach(MIMEText(body_text, "plain"))
    if body_html:
        msg.attach(MIMEText(body_html, "html"))

    try:
        port = int(getattr(settings, "SMTP_PORT", 587))
        use_tls = str(getattr(settings, "SMTP_TLS", "true")).lower() == "true"

        with smtplib.SMTP(settings.SMTP_HOST, port, timeout=15) as server:
            if use_tls:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, to_address, msg.as_string())

        logger.info("Email sent via SMTP to %s | subject: %s", to_address, subject)
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed — check SMTP_USER / SMTP_PASSWORD")
        return False
    except smtplib.SMTPException as exc:
        logger.error("SMTP error sending to %s: %s", to_address, exc)
        return False
    except Exception as exc:
        logger.error("Unexpected error sending email to %s: %s", to_address, exc)
        return False


def _send_via_sendgrid(
    to_address: str,
    subject: str,
    body_text: str,
    body_html: Optional[str],
) -> bool:
    """
    Send via SendGrid API.
    Requires: pip install sendgrid
    """
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

        sg = SendGridAPIClient(sg_api_key)
        response = sg.send(message)

        if response.status_code in (200, 201, 202):
            logger.info("Email sent via SendGrid to %s | status=%s", to_address, response.status_code)
            return True

        logger.error(
            "SendGrid returned status %s for %s", response.status_code, to_address
        )
        return False

    except ImportError:
        logger.error(
            "sendgrid package not installed. Run: pip install sendgrid"
        )
        return False
    except Exception as exc:
        logger.error("SendGrid error sending to %s: %s", to_address, exc)
        return False
