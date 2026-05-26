"""
app/models/user.py

Platform user — internal staff or a customer-side login.

Roles (from SQL schema):
    SUPER_ADMIN, ADMIN, WAREHOUSE, QA, DOCUMENTATION, CUSTOMER

A CUSTOMER-role user is linked to a Customer record via customer_id.
Internal staff have customer_id = NULL.

SQL reference: users table
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.audit_log import AuditLog
    from app.models.customer import Customer
    from app.models.media_file import MediaFile
    from app.models.milestone import Milestone
    from app.models.notification import Notification
    from app.models.order import Order
    from app.models.order_comment import OrderComment
    from app.models.qa_report import QAReport
    from app.models.document import Document
    from app.models.login_session import LoginSession


# Match the SQL ENUM exactly
class UserRoleSQL:
    values = ("SUPER_ADMIN", "ADMIN", "WAREHOUSE", "QA", "DOCUMENTATION", "CUSTOMER")


class User(Base):
    __tablename__ = "users"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        "user_id", primary_key=True, autoincrement=True
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # ── Role ──────────────────────────────────────────────────────────────────
    role: Mapped[str] = mapped_column(
        Enum(*UserRoleSQL.values, name="user_role_enum"),
        nullable=False,
    )

    # ── Customer link (only for CUSTOMER role) ────────────────────────────────
    customer_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("customers.customer_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Soft delete ───────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── MFA (Multi-Factor Authentication) ─────────────────────────────────────
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    totp_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    customer: Mapped[Optional["Customer"]] = relationship(
        "Customer", back_populates="users"
    )
    orders_created: Mapped[List["Order"]] = relationship(
        "Order", back_populates="creator", foreign_keys="Order.created_by", lazy="select"
    )
    milestones_completed: Mapped[List["Milestone"]] = relationship(
        "Milestone", back_populates="completer", foreign_keys="Milestone.completed_by", lazy="select"
    )
    media_uploaded: Mapped[List["MediaFile"]] = relationship(
        "MediaFile", back_populates="uploader", lazy="select"
    )
    documents_uploaded: Mapped[List["Document"]] = relationship(
        "Document", back_populates="uploader", lazy="select"
    )
    qa_reports_verified: Mapped[List["QAReport"]] = relationship(
        "QAReport", back_populates="verifier", lazy="select"
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification", back_populates="user", lazy="select"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="user", lazy="select"
    )
    comments: Mapped[List["OrderComment"]] = relationship(
        "OrderComment", back_populates="user", lazy="select"
    )
    login_sessions: Mapped[List["LoginSession"]] = relationship(
        "LoginSession", back_populates="user", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email='{self.email}' role='{self.role}'>"
