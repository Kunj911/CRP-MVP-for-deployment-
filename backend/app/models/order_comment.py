"""
app/models/order_comment.py

Internal comments on an order — visible only to staff (not customers).

Used by warehouse, QA, docs team, and admins to communicate
context about a specific order without creating a formal milestone.

SQL reference: order_comments table
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.user import User


class OrderComment(Base):
    __tablename__ = "order_comments"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        "comment_id", primary_key=True, autoincrement=True
    )

    # ── Foreign keys ──────────────────────────────────────────────────────────
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.order_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Content ───────────────────────────────────────────────────────────────
    comment: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Timestamp ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    order: Mapped["Order"] = relationship("Order", back_populates="comments")
    user: Mapped["User"] = relationship("User", back_populates="comments")

    def __repr__(self) -> str:
        return (
            f"<OrderComment id={self.id} order_id={self.order_id} "
            f"user_id={self.user_id}>"
        )
