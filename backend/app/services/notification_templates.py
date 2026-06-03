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


def _button(url: str, label: str, color: str = "#E6820A") -> str:
    return (
        f'<a href="{url}" style="display:inline-block;background:{color};color:#fff;'
        "padding:12px 20px;text-decoration:none;border-radius:6px;"
        'font-weight:bold;margin-top:8px;">'
        f"{label}</a>"
    )


def _email_shell(title: str, body: str) -> str:
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:620px;margin:auto;color:#1f2937;">
      <div style="background:#3A6B4A;padding:22px;border-radius:8px 8px 0 0;">
        <h2 style="color:#ffffff;margin:0;">Client Relationship Portal</h2>
        <p style="color:#D3EBD9;margin:4px 0 0;">{title}</p>
      </div>
      <div style="background:#FAFAF7;padding:24px;border:1px solid #EDE6D6;border-top:0;border-radius:0 0 8px 8px;">
        {body}
        <p style="color:#6b7280;font-size:12px;margin-top:24px;">
          This is an automated transactional email from the Client Relationship Portal.
        </p>
      </div>
    </div>
    """


@dataclass
class EmailTemplate:
    subject: str
    body_text: str
    body_html: str


def login_alert_email(
    full_name: str,
    role: str,
    login_time: str,
    ip_address: str,
    user_agent: str,
    dashboard_url: str,
) -> EmailTemplate:
    subject = "[CRP] New admin login detected"
    body_text = (
        f"Hello {full_name},\n\n"
        "A login was recorded for your CRP account.\n\n"
        f"Role: {role}\n"
        f"Time: {login_time} UTC\n"
        f"IP address: {ip_address or 'Unknown'}\n"
        f"Device: {user_agent or 'Unknown'}\n\n"
        "If this was you, no action is needed. If you do not recognize this login, change your password immediately."
    )
    body_html = _email_shell(
        "Security alert",
        f"""
        <p>Hello <strong>{full_name}</strong>,</p>
        <p>A login was recorded for your CRP account.</p>
        <div style="background:#FFF8EC;border-left:4px solid #E6820A;padding:12px 16px;border-radius:4px;">
          <p><strong>Role:</strong> {role}</p>
          <p><strong>Time:</strong> {login_time} UTC</p>
          <p><strong>IP address:</strong> {ip_address or 'Unknown'}</p>
          <p><strong>Device:</strong> {user_agent or 'Unknown'}</p>
        </div>
        <p>If this was you, no action is needed. If not, change your password immediately.</p>
        {_button(dashboard_url, "Open Portal")}
        """,
    )
    return EmailTemplate(subject=subject, body_text=body_text, body_html=body_html)


def password_reset_email(
    full_name: str,
    reset_url: str,
    expires_minutes: int = 30,
) -> EmailTemplate:
    subject = "[CRP] Reset your password"
    body_text = (
        f"Hello {full_name},\n\n"
        "Use the link below to reset your password.\n\n"
        f"{reset_url}\n\n"
        f"This link expires in {expires_minutes} minutes. If you did not request this, ignore this email."
    )
    body_html = _email_shell(
        "Password reset",
        f"""
        <p>Hello <strong>{full_name}</strong>,</p>
        <p>Use the button below to reset your password.</p>
        {_button(reset_url, "Reset Password")}
        <p>This link expires in {expires_minutes} minutes. If you did not request this, ignore this email.</p>
        """,
    )
    return EmailTemplate(subject=subject, body_text=body_text, body_html=body_html)


def customer_created_email(
    company_name: str,
    contact_name: str,
    portal_url: str,
) -> EmailTemplate:
    subject = "[CRP] Your customer portal is ready"
    greeting = contact_name or company_name
    body_text = (
        f"Hello {greeting},\n\n"
        f"Your customer portal for {company_name} is ready.\n\n"
        f"Portal: {portal_url}\n\n"
        "You can use the portal to track orders, documents, and shipment updates."
    )
    body_html = _email_shell(
        "Welcome",
        f"""
        <p>Hello <strong>{greeting}</strong>,</p>
        <p>Your customer portal for <strong>{company_name}</strong> is ready.</p>
        <p>You can use it to track orders, documents, and shipment updates.</p>
        {_button(portal_url, "Open Portal", "#3A6B4A")}
        """,
    )
    return EmailTemplate(subject=subject, body_text=body_text, body_html=body_html)


def order_created_email(
    order_code: str,
    customer_name: str,
    product_name: str,
    portal_url: str,
) -> EmailTemplate:
    subject = f"[CRP] Order {order_code} created"
    order_url = f"{portal_url.rstrip('/')}/orders/{order_code}"
    body_text = (
        f"Dear {customer_name},\n\n"
        "A new order has been created in your portal.\n\n"
        f"Order: {order_code}\n"
        f"Product: {product_name}\n\n"
        f"Track it here:\n{order_url}\n\n"
        "You will receive updates as the order progresses."
    )
    body_html = _email_shell(
        "Order created",
        f"""
        <p>Dear <strong>{customer_name}</strong>,</p>
        <p>A new order has been created in your portal.</p>
        <div style="background:#EAF5ED;border-left:4px solid #3A6B4A;padding:12px 16px;border-radius:4px;">
          <p><strong>Order:</strong> {order_code}</p>
          <p><strong>Product:</strong> {product_name}</p>
        </div>
        {_button(order_url, "Track Order", "#3A6B4A")}
        """,
    )
    return EmailTemplate(subject=subject, body_text=body_text, body_html=body_html)


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
