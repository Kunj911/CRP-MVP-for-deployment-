"""
app/models/document.py

Stores shipment documents (Invoice, BL Copy, COA, Lab Report, etc.)
uploaded by the Docs Team or Admin.

Customers can download these from the Document Vault once uploaded.

SQL reference: documents table
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Enum, ForeignKey, Index, String, Text, func, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.user import User


class Document(Base):
    __tablename__ = "documents"

    __table_args__ = (
        Index("idx_documents_order", "order_id"),
    )

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        "document_id", primary_key=True, autoincrement=True
    )

    # ── Foreign keys ──────────────────────────────────────────────────────────
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.order_id", ondelete="CASCADE"),
        nullable=False,
    )
    uploaded_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Document metadata ─────────────────────────────────────────────────────
    document_type: Mapped[str] = mapped_column(
        Enum(
            "INVOICE",
            "BL_COPY",
            "COA",
            "PHYTOSANITARY_CERTIFICATE",
            "LAB_REPORT",
            "PACKING_LIST",
            "OTHER",
            "bill_of_lading",
            "certificate_of_analysis",
            "product_specification",
            "insurance_certificate",
            "purchase_order",
            "certificate_of_origin",
            name="document_type_enum",
        ),
        nullable=False,
        index=True,
    )
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    storage_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    status: Mapped[str] = mapped_column(
        Enum(
            "draft",
            "uploaded",
            "under_review",
            "approved",
            "rejected",
            "archived",
            name="document_status_enum",
        ),
        default="uploaded",
        nullable=False,
        index=True,
    )
    visibility: Mapped[str] = mapped_column(
        Enum(
            "internal",
            "customer_visible",
            "admin_only",
            name="document_visibility_enum",
        ),
        default="internal",
        nullable=False,
        index=True,
    )
    reviewed_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)

    # ── Timestamp ─────────────────────────────────────────────────────────────
    uploaded_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    order: Mapped["Order"] = relationship("Order", back_populates="documents")
    uploader: Mapped[Optional["User"]] = relationship(
        "User", back_populates="documents_uploaded", foreign_keys=[uploaded_by]
    )
    reviewer: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[reviewed_by]
    )

    def __repr__(self) -> str:
        return (
            f"<Document id={self.id} order_id={self.order_id} "
            f"type='{self.document_type}'>"
        )
