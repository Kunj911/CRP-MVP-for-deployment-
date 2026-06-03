"""
app/models/order_document_requirement.py

Tracks checklist requirements for orders, mapping whether specific document categories
are required, uploaded, and approved.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum, ForeignKey, Index, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.user import User
    from app.models.document import Document


class OrderDocumentRequirement(Base):
    __tablename__ = "order_document_requirements"

    __table_args__ = (
        Index("uq_order_doc_type", "order_id", "document_type", unique=True),
    )

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        "requirement_id", primary_key=True, autoincrement=True
    )

    # ── Foreign keys ──────────────────────────────────────────────────────────
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.order_id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("documents.document_id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Requirement Status ────────────────────────────────────────────────────
    document_type: Mapped[str] = mapped_column(
        Enum(
            'invoice', 'bill_of_lading', 'lab_report', 'packing_list', 'certificate_of_analysis', 
            'phytosanitary_certificate', 'product_specification', 'insurance_certificate', 
            'purchase_order', 'certificate_of_origin', 'other',
            name="order_document_requirement_type_enum"
        ),
        nullable=False,
    )
    required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    uploaded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    uploaded_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    order: Mapped["Order"] = relationship("Order", back_populates="document_requirements")
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by])
    document: Mapped[Optional["Document"]] = relationship("Document", foreign_keys=[document_id])

    def __repr__(self) -> str:
        return (
            f"<OrderDocumentRequirement id={self.id} order_id={self.order_id} "
            f"type='{self.document_type}' required={self.required} "
            f"uploaded={self.uploaded} approved={self.approved}>"
        )
