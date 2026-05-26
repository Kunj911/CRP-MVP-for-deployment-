"""
app/models/qa_report.py

Quality Assurance report for a shipment order.

Stores spice QA parameters: moisture level, purity percentage,
contamination status, and an optional attached document.

The QA Team creates and verifies these reports. Customers can
view them in read-only mode.

SQL reference: qa_reports table
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.order import Order
    from app.models.user import User


class QAReport(Base):
    __tablename__ = "qa_reports"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        "qa_report_id", primary_key=True, autoincrement=True
    )

    # ── Foreign keys ──────────────────────────────────────────────────────────
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.order_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    report_document_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("documents.document_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    verified_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── QA parameters ─────────────────────────────────────────────────────────
    moisture_level: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    purity_percentage: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    contamination_status: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Verification timestamp ────────────────────────────────────────────────
    verified_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    order: Mapped["Order"] = relationship("Order", back_populates="qa_reports")
    report_document: Mapped[Optional["Document"]] = relationship(
        "Document", back_populates="qa_reports"
    )
    verifier: Mapped[Optional["User"]] = relationship(
        "User", back_populates="qa_reports_verified"
    )

    def __repr__(self) -> str:
        return (
            f"<QAReport id={self.id} order_id={self.order_id} "
            f"purity={self.purity_percentage}%>"
        )
