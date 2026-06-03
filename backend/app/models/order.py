"""
app/models/order.py

Core shipment / export order record.

shipment_status tracks the high-level stage of the order and mirrors
the milestone progression. It is updated by the order_service when
a milestone is completed.

SQL reference: orders table
"""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Date,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.audit_log import AuditLog
    from app.models.customer import Customer
    from app.models.document import Document
    from app.models.media_file import MediaFile
    from app.models.milestone import Milestone
    from app.models.notification import Notification
    from app.models.user import User
    from app.models.order_document_requirement import OrderDocumentRequirement
    from app.models.order_event import OrderEvent



class Order(Base):
    __tablename__ = "orders"

    __table_args__ = (
        Index("idx_orders_customer", "customer_id"),
        Index("idx_orders_status", "shipment_status"),
    )

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        "order_id", primary_key=True, autoincrement=True
    )

    # ── Order identity ────────────────────────────────────────────────────────
    order_code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )

    # ── Foreign keys ──────────────────────────────────────────────────────────
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.customer_id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Product details ───────────────────────────────────────────────────────
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # ── Status ────────────────────────────────────────────────────────────────
    shipment_status: Mapped[str] = mapped_column(
        Enum(
            "CREATED",
            "PROCUREMENT",
            "QA_TESTING",
            "PACKAGING",
            "DOCUMENTATION",
            "READY_FOR_SHIPMENT",
            "SHIPPED",
            "DELIVERED",
            name="shipment_status_enum",
        ),
        default="CREATED",
        nullable=False,
    )

    # ── Dates ─────────────────────────────────────────────────────────────────
    expected_dispatch_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True
    )
    expected_delivery_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True
    )

    # ── Notes ─────────────────────────────────────────────────────────────────
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    customer: Mapped["Customer"] = relationship(
        "Customer", back_populates="orders"
    )
    creator: Mapped[Optional["User"]] = relationship(
        "User", back_populates="orders_created", foreign_keys=[created_by]
    )
    milestones: Mapped[List["Milestone"]] = relationship(
        "Milestone", back_populates="order", cascade="all, delete-orphan", lazy="select"
    )
    media_files: Mapped[List["MediaFile"]] = relationship(
        "MediaFile", back_populates="order", cascade="all, delete-orphan", lazy="select"
    )
    documents: Mapped[List["Document"]] = relationship(
        "Document", back_populates="order", cascade="all, delete-orphan", lazy="select"
    )
    notifications: Mapped[List["Notification"]] = relationship(
    "Notification",back_populates="order",foreign_keys="Notification.order_id",cascade="all, delete-orphan",lazy="select"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="order", lazy="select"
    )
    document_requirements: Mapped[List["OrderDocumentRequirement"]] = relationship(
        "OrderDocumentRequirement", back_populates="order", cascade="all, delete-orphan", lazy="select"
    )
    events: Mapped[List["OrderEvent"]] = relationship(
        "OrderEvent", back_populates="order", cascade="all, delete-orphan", lazy="select"
    )


    def __repr__(self) -> str:
        return (
            f"<Order id={self.id} code='{self.order_code}' "
            f"status='{self.shipment_status}'>"
        )
