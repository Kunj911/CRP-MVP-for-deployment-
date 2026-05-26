"""
app/models/media_file.py

Stores uploaded images (procurement, packaging, QA, loading photos).
Optionally linked to a specific milestone for timeline context.

SQL reference: media_files table
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum, ForeignKey, Index, String, Text, func, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.milestone import Milestone
    from app.models.order import Order
    from app.models.user import User


class MediaFile(Base):
    __tablename__ = "media_files"

    __table_args__ = (
        Index("idx_media_order", "order_id"),
    )

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        "media_id", primary_key=True, autoincrement=True
    )

    # ── Foreign keys ──────────────────────────────────────────────────────────
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.order_id", ondelete="CASCADE"),
        nullable=False,
    )
    milestone_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("milestones.milestone_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    uploaded_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Media metadata ────────────────────────────────────────────────────────
    media_type: Mapped[str] = mapped_column(
        Enum(
            "PROCUREMENT_IMAGE",
            "PACKAGING_IMAGE",
            "QA_IMAGE",
            "LOADING_IMAGE",
            name="media_type_enum",
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
    order: Mapped["Order"] = relationship("Order", back_populates="media_files")
    milestone: Mapped[Optional["Milestone"]] = relationship(
        "Milestone", back_populates="media_files"
    )
    uploader: Mapped[Optional["User"]] = relationship(
        "User", back_populates="media_uploaded"
    )

    def __repr__(self) -> str:
        return (
            f"<MediaFile id={self.id} order_id={self.order_id} "
            f"type='{self.media_type}'>"
        )
