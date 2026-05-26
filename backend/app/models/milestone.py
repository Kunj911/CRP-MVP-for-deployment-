"""
app/models/milestone.py

Tracks individual stages in a shipment's lifecycle.

stage_name uses the 9-stage enum from the SQL schema.
When a milestone is marked COMPLETED, milestone_service triggers
a notification to the customer.

SQL reference: milestones table
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Enum, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.media_file import MediaFile
    from app.models.order import Order
    from app.models.user import User


class Milestone(Base):
    __tablename__ = "milestones"

    __table_args__ = (
        Index("idx_milestones_order", "order_id"),
    )

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        "milestone_id", primary_key=True, autoincrement=True
    )

    # ── Foreign keys ──────────────────────────────────────────────────────────
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.order_id", ondelete="CASCADE"),
        nullable=False,
    )
    completed_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Stage ─────────────────────────────────────────────────────────────────
    stage_name: Mapped[str] = mapped_column(
        Enum(
            "PROCUREMENT",
            "RAW_MATERIAL_VERIFIED",
            "QA_TESTING",
            "PACKAGING_STARTED",
            "PACKAGING_COMPLETED",
            "DOCUMENTS_UPLOADED",
            "CONTAINER_LOADING",
            "SHIPMENT_DISPATCHED",
            "DELIVERED",
            name="milestone_stage_enum",
        ),
        nullable=False,
        index=True,
    )

    # ── Status ────────────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        Enum("PENDING", "IN_PROGRESS", "COMPLETED", name="milestone_status_enum"),
        default="PENDING",
        nullable=False,
        index=True,
    )

    # ── Details ───────────────────────────────────────────────────────────────
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Completion timestamp ──────────────────────────────────────────────────
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    order: Mapped["Order"] = relationship("Order", back_populates="milestones")
    completer: Mapped[Optional["User"]] = relationship(
        "User", back_populates="milestones_completed", foreign_keys=[completed_by]
    )
    media_files: Mapped[List["MediaFile"]] = relationship(
        "MediaFile", back_populates="milestone", lazy="select"
    )

    def __repr__(self) -> str:
        return (
            f"<Milestone id={self.id} order_id={self.order_id} "
            f"stage='{self.stage_name}' status='{self.status}'>"
        )
