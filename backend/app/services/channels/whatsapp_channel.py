"""
app/services/channels/whatsapp_channel.py

WhatsApp notification channel adapter.

Architecture:
  - Supports Twilio WhatsApp API (production-ready)
  - Supports Meta Cloud API (alternative)
  - Gracefully no-ops if credentials not configured (dev safety)

Configuration (.env):
  WHATSAPP_PROVIDER=twilio   # or: meta
  TWILIO_ACCOUNT_SID=ACxxxxxxxx
  TWILIO_AUTH_TOKEN=xxxxxxxxxx
  TWILIO_WHATSAPP_FROM=whatsapp:+14155238886  # Twilio sandbox/prod number

  # Meta Cloud API alternative:
  # WHATSAPP_PROVIDER=meta
  # META_WHATSAPP_TOKEN=EAAxxxxxx
  # META_PHONE_NUMBER_ID=123456789
"""

import logging
from typing import Optional

from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def send_whatsapp(
    to_phone: str,
    message: str,
) -> bool:
    """
    Send a WhatsApp message via the configured provider.

    Args:
        to_phone: Recipient phone number in E.164 format e.g. "+919876543210"
        message:  Message body (plain text, max 1024 chars for templates)

    Returns:
        True  — message accepted
        False — delivery failed
    """
    provider = getattr(settings, "WHATSAPP_PROVIDER", "").lower()

    if not provider:
        logger.warning(
            "WhatsApp not configured — skipping send to %s. "
            "Set WHATSAPP_PROVIDER in .env",
            to_phone,
        )
        return False

    if provider == "twilio":
        return _send_via_twilio(to_phone, message)

    if provider == "meta":
        return _send_via_meta(to_phone, message)

    logger.error(
        "Unknown WHATSAPP_PROVIDER: '%s'. Expected 'twilio' or 'meta'.", provider
    )
    return False


def _send_via_twilio(to_phone: str, message: str) -> bool:
    """
    Send via Twilio WhatsApp API.
    Requires: pip install twilio
    """
    try:
        from twilio.rest import Client  # type: ignore

        account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", "")
        auth_token  = getattr(settings, "TWILIO_AUTH_TOKEN", "")
        from_number = getattr(settings, "TWILIO_WHATSAPP_FROM", "")

        if not all([account_sid, auth_token, from_number]):
            logger.error(
                "Twilio credentials incomplete. "
                "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM"
            )
            return False

        client = Client(account_sid, auth_token)
        twilio_msg = client.messages.create(
            body=message,
            from_=from_number,
            to=f"whatsapp:{to_phone}",
        )

        logger.info(
            "WhatsApp sent via Twilio to %s | sid=%s status=%s",
            to_phone, twilio_msg.sid, twilio_msg.status,
        )
        return twilio_msg.status not in ("failed", "undelivered")

    except ImportError:
        logger.error("twilio package not installed. Run: pip install twilio")
        return False
    except Exception as exc:
        logger.error("Twilio WhatsApp error to %s: %s", to_phone, exc)
        return False


def _send_via_meta(to_phone: str, message: str) -> bool:
    """
    Send via Meta Cloud API (WhatsApp Business API).
    Requires: pip install requests
    """
    try:
        import requests  # type: ignore

        token          = getattr(settings, "META_WHATSAPP_TOKEN", "")
        phone_id       = getattr(settings, "META_PHONE_NUMBER_ID", "")

        if not all([token, phone_id]):
            logger.error(
                "Meta WhatsApp credentials incomplete. "
                "Set META_WHATSAPP_TOKEN, META_PHONE_NUMBER_ID"
            )
            return False

        url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "text",
            "text": {"body": message},
        }

        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()

        logger.info(
            "WhatsApp sent via Meta Cloud API to %s | response=%s",
            to_phone, response.status_code,
        )
        return True

    except Exception as exc:
        logger.error("Meta WhatsApp API error to %s: %s", to_phone, exc)
        return False
