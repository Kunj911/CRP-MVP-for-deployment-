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
    from app.models.qa_report import QAReport
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
            name="document_type_enum",
        ),
        nullable=False,
        index=True,
    )
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    storage_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # ── Timestamp ─────────────────────────────────────────────────────────────
    uploaded_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    order: Mapped["Order"] = relationship("Order", back_populates="documents")
    uploader: Mapped[Optional["User"]] = relationship(
        "User", back_populates="documents_uploaded"
    )
    # A QA report may reference this document as its report attachment
    qa_reports: Mapped[List["QAReport"]] = relationship(
        "QAReport", back_populates="report_document", lazy="select"
    )

    def __repr__(self) -> str:
        return (
            f"<Document id={self.id} order_id={self.order_id} "
            f"type='{self.document_type}'>"
        )
