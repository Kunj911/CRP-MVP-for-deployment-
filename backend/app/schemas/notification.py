"""
app/schemas/notification.py

Pydantic schemas for the Notification module.

Covers:
  - Notification channel types (EMAIL, WHATSAPP, SMS)
  - Delivery status tracking
  - Event trigger types for the notification engine
  - API response schemas for listing notifications
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


# ── Enums matching notifications table ───────────────────────────────────────

class NotificationChannel(str, Enum):
    EMAIL     = "EMAIL"
    WHATSAPP  = "WHATSAPP"
    SMS       = "SMS"


class DeliveryStatus(str, Enum):
    PENDING = "PENDING"
    SENT    = "SENT"
    FAILED  = "FAILED"


# ── Event types that can trigger notifications ────────────────────────────────

class NotificationEvent(str, Enum):
    """
    Internal enum — NOT stored in DB.
    Used by the trigger system to decide which template and recipients to use.
    """
    MILESTONE_COMPLETED    = "MILESTONE_COMPLETED"
    DOCUMENT_UPLOADED      = "DOCUMENT_UPLOADED"
    SHIPMENT_DISPATCHED    = "SHIPMENT_DISPATCHED"
    ORDER_CREATED          = "ORDER_CREATED"          # future
    ORDER_STATUS_CHANGED   = "ORDER_STATUS_CHANGED"   # future


# ── Response schemas ──────────────────────────────────────────────────────────

class NotificationResponse(BaseModel):
    """Returned when listing notifications for the current user."""
    id: int
    order_id: int
    user_id: int
    notification_type: Optional[NotificationChannel]
    message: Optional[str]
    delivery_status: DeliveryStatus
    sent_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}
