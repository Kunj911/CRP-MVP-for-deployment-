"""
app/services/notification_templates.py

Message templates for every notification event and channel.

Design:
  - All message text lives HERE, not scattered in business logic
  - Each function returns (subject, body_text, body_html) for email
    and (message,) for WhatsApp/SMS
  - Templates use Python f-strings — safe, no external template engine needed
  - Extend: add a new event, add a new function, wire it in notification_service.py

Events:
  - MILESTONE_COMPLETED
  - DOCUMENT_UPLOADED
  - SHIPMENT_DISPATCHED
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class EmailTemplate:
    subject: str
    body_text: str
    body_html: str


@dataclass
class ShortTemplate:
    """For WhatsApp / SMS — single message string."""
    message: str


# ── MILESTONE COMPLETED ───────────────────────────────────────────────────────

def milestone_completed_email(
    order_code: str,
    stage_label: str,
    customer_name: str,
    completed_at: str,
    dashboard_url: str = "https://app.live-trace.com",
) -> EmailTemplate:
    subject = f"[Live-Trace] Order {order_code} — {stage_label} Completed"

    body_text = (
        f"Dear {customer_name},\n\n"
        f"Your order {order_code} has reached a new milestone.\n\n"
        f"Stage completed: {stage_label}\n"
        f"Completed at:   {completed_at} (UTC)\n\n"
        f"Track your order in real time:\n{dashboard_url}/orders/{order_code}\n\n"
        f"If you have any questions, please contact your export manager.\n\n"
        f"Regards,\nThe Live-Trace Team"
    )

    body_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
      <div style="background:#1a1a2e; padding:24px; border-radius:8px 8px 0 0;">
        <h2 style="color:#ffffff; margin:0;">Live-Trace</h2>
        <p style="color:#a0aec0; margin:4px 0 0;">Export Tracking Platform</p>
      </div>
      <div style="background:#f7fafc; padding:24px; border-radius:0 0 8px 8px;">
        <p style="font-size:16px;">Dear <strong>{customer_name}</strong>,</p>
        <p>Your order <strong>{order_code}</strong> has completed a new stage:</p>
        <div style="background:#e6fffa; border-left:4px solid #38b2ac; padding:12px 16px; border-radius:4px; margin:16px 0;">
          <strong style="font-size:18px; color:#2c7a7b;">✅ {stage_label}</strong><br/>
          <span style="color:#718096; font-size:13px;">Completed at {completed_at} UTC</span>
        </div>
        <a href="{dashboard_url}/orders/{order_code}"
           style="display:inline-block; background:#667eea; color:#fff; padding:12px 24px;
                  text-decoration:none; border-radius:6px; font-weight:bold; margin-top:8px;">
          Track Your Order →
        </a>
        <p style="color:#718096; font-size:12px; margin-top:24px;">
          You're receiving this because you have an active order with us.
        </p>
      </div>
    </div>
    """
    return EmailTemplate(subject=subject, body_text=body_text, body_html=body_html)


def milestone_completed_whatsapp(
    order_code: str,
    stage_label: str,
    completed_at: str,
) -> ShortTemplate:
    message = (
        f"🚀 *Live-Trace Update*\n\n"
        f"Your order *{order_code}* has completed the *{stage_label}* stage.\n"
        f"✅ Completed at: {completed_at} UTC\n\n"
        f"Track your order: https://app.live-trace.com/orders/{order_code}"
    )
    return ShortTemplate(message=message)


# ── DOCUMENT UPLOADED ─────────────────────────────────────────────────────────

def document_uploaded_email(
    order_code: str,
    document_type: str,
    file_name: str,
    customer_name: str,
    uploaded_at: str,
    dashboard_url: str = "https://app.live-trace.com",
) -> EmailTemplate:
    doc_label = document_type.replace("_", " ").title()
    subject = f"[Live-Trace] New Document Available — Order {order_code}"

    body_text = (
        f"Dear {customer_name},\n\n"
        f"A new document has been uploaded for your order {order_code}.\n\n"
        f"Document type: {doc_label}\n"
        f"File name:     {file_name}\n"
        f"Uploaded at:   {uploaded_at} (UTC)\n\n"
        f"Access your documents:\n{dashboard_url}/orders/{order_code}/documents\n\n"
        f"Regards,\nThe Live-Trace Team"
    )

    body_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
      <div style="background:#1a1a2e; padding:24px; border-radius:8px 8px 0 0;">
        <h2 style="color:#ffffff; margin:0;">Live-Trace</h2>
      </div>
      <div style="background:#f7fafc; padding:24px; border-radius:0 0 8px 8px;">
        <p style="font-size:16px;">Dear <strong>{customer_name}</strong>,</p>
        <p>A new document has been uploaded for order <strong>{order_code}</strong>:</p>
        <div style="background:#ebf8ff; border-left:4px solid #4299e1; padding:12px 16px; border-radius:4px; margin:16px 0;">
          <strong style="color:#2b6cb0;">📄 {doc_label}</strong><br/>
          <span style="color:#718096; font-size:13px;">{file_name} &nbsp;·&nbsp; {uploaded_at} UTC</span>
        </div>
        <a href="{dashboard_url}/orders/{order_code}/documents"
           style="display:inline-block; background:#4299e1; color:#fff; padding:12px 24px;
                  text-decoration:none; border-radius:6px; font-weight:bold; margin-top:8px;">
          View Documents →
        </a>
      </div>
    </div>
    """
    return EmailTemplate(subject=subject, body_text=body_text, body_html=body_html)


def document_uploaded_whatsapp(
    order_code: str,
    document_type: str,
    file_name: str,
) -> ShortTemplate:
    doc_label = document_type.replace("_", " ").title()
    message = (
        f"📄 *Live-Trace* — New Document\n\n"
        f"Order *{order_code}*: A *{doc_label}* has been uploaded.\n"
        f"File: {file_name}\n\n"
        f"View: https://app.live-trace.com/orders/{order_code}/documents"
    )
    return ShortTemplate(message=message)


# ── SHIPMENT DISPATCHED ───────────────────────────────────────────────────────

def shipment_dispatched_email(
    order_code: str,
    customer_name: str,
    dispatched_at: str,
    vessel_name: Optional[str] = None,
    bl_number: Optional[str] = None,
    dashboard_url: str = "https://app.live-trace.com",
) -> EmailTemplate:
    subject = f"[Live-Trace] Your Shipment is Dispatched — Order {order_code}"

    vessel_line = f"Vessel: {vessel_name}\n" if vessel_name else ""
    bl_line     = f"BL Number: {bl_number}\n" if bl_number else ""

    body_text = (
        f"Dear {customer_name},\n\n"
        f"Great news! Your shipment for order {order_code} has been dispatched.\n\n"
        f"Dispatched at: {dispatched_at} (UTC)\n"
        f"{vessel_line}{bl_line}\n"
        f"Track your shipment:\n{dashboard_url}/orders/{order_code}\n\n"
        f"Regards,\nThe Live-Trace Team"
    )

    vessel_html = f"<li><strong>Vessel:</strong> {vessel_name}</li>" if vessel_name else ""
    bl_html     = f"<li><strong>BL Number:</strong> {bl_number}</li>" if bl_number else ""

    body_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
      <div style="background:#1a1a2e; padding:24px; border-radius:8px 8px 0 0;">
        <h2 style="color:#ffffff; margin:0;">Live-Trace</h2>
      </div>
      <div style="background:#f7fafc; padding:24px; border-radius:0 0 8px 8px;">
        <p style="font-size:16px;">Dear <strong>{customer_name}</strong>,</p>
        <p style="font-size:18px;">🚢 Your shipment for order <strong>{order_code}</strong> is on its way!</p>
        <div style="background:#fef9e7; border-left:4px solid #f6ad55; padding:12px 16px; border-radius:4px; margin:16px 0;">
          <ul style="margin:0; padding-left:16px; color:#744210;">
            <li><strong>Dispatched at:</strong> {dispatched_at} UTC</li>
            {vessel_html}{bl_html}
          </ul>
        </div>
        <a href="{dashboard_url}/orders/{order_code}"
           style="display:inline-block; background:#ed8936; color:#fff; padding:12px 24px;
                  text-decoration:none; border-radius:6px; font-weight:bold; margin-top:8px;">
          Track Shipment →
        </a>
      </div>
    </div>
    """
    return EmailTemplate(subject=subject, body_text=body_text, body_html=body_html)


def shipment_dispatched_whatsapp(
    order_code: str,
    dispatched_at: str,
    vessel_name: Optional[str] = None,
) -> ShortTemplate:
    vessel_line = f"\nVessel: {vessel_name}" if vessel_name else ""
    message = (
        f"🚢 *Live-Trace* — Shipment Dispatched!\n\n"
        f"Order *{order_code}* has been dispatched.{vessel_line}\n"
        f"⏱ {dispatched_at} UTC\n\n"
        f"Track: https://app.live-trace.com/orders/{order_code}"
    )
    return ShortTemplate(message=message)
