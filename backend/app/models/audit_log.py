"""
app/models/audit_log.py

Immutable record of every state-changing action on the platform.

Every create / update / delete / upload / login action is logged here
by audit_service.log_action(). Records are never deleted.

target_table + target_id together identify what was modified.

SQL reference: audit_logs table
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.user import User


class AuditLog(Base):
    __tablename__ = "audit_logs"

    __table_args__ = (
        Index("idx_audit_user", "user_id"),
        Index("idx_audit_order", "order_id"),
    )

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        "audit_id", primary_key=True, autoincrement=True
    )

    # ── Who acted ────────────────────────────────────────────────────────────
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── What happened ─────────────────────────────────────────────────────────
    action_type: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )

    # ── What was affected ─────────────────────────────────────────────────────
    target_table: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    target_id: Mapped[Optional[int]] = mapped_column(nullable=True)

    # ── Optional order context (for quick order-scoped audit queries) ─────────
    order_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("orders.order_id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Human-readable description ────────────────────────────────────────────
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Timestamp (immutable — no updated_at) ─────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="audit_logs"
    )
    order: Mapped[Optional["Order"]] = relationship(
        "Order", back_populates="audit_logs"
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} action='{self.action_type}' "
            f"table='{self.target_table}' target_id={self.target_id}>"
        )
