"""
app/models/notification.py

Tracks outbound notifications sent to users (Email / WhatsApp / SMS).

A notification is triggered by an event (milestone completed, document
uploaded, etc.) and is always tied to an order and a recipient user.

delivery_status tracks whether the message was sent successfully.

SQL reference: notifications table
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum, ForeignKey, Index, Text, func, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.user import User
    from app.models.document import Document


class Notification(Base):
    __tablename__ = "notifications"

    __table_args__ = (
        Index("idx_notifications_order", "order_id"),
        Index("idx_notifications_user", "user_id"),
    )

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        "notification_id", primary_key=True, autoincrement=True
    )

    # ── Foreign keys ──────────────────────────────────────────────────────────
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.order_id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    related_order_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("orders.order_id", ondelete="CASCADE"),
        nullable=True,
    )
    related_document_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("documents.document_id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Notification details ──────────────────────────────────────────────────
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notification_type: Mapped[str] = mapped_column(
        Enum(
            "EMAIL", "WHATSAPP", "SMS", "order", "document", "shipment", "system", "qa", "payment",
            name="notification_channel_enum"
        ),
        nullable=False,
    )
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # ── Delivery tracking ─────────────────────────────────────────────────────
    delivery_status: Mapped[str] = mapped_column(
        Enum("PENDING", "SENT", "FAILED", name="delivery_status_enum"),
        default="PENDING",
        nullable=False,
        index=True,
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    order: Mapped["Order"] = relationship("Order", back_populates="notifications", foreign_keys=[order_id])
    user: Mapped["User"] = relationship("User", back_populates="notifications")
    related_order: Mapped[Optional["Order"]] = relationship("Order", foreign_keys=[related_order_id])
    related_document: Mapped[Optional["Document"]] = relationship("Document", foreign_keys=[related_document_id])

    def __repr__(self) -> str:
        return (
            f"<Notification id={self.id} order_id={self.order_id} "
            f"type='{self.notification_type}' status='{self.delivery_status}' is_read={self.is_read}>"
        )

