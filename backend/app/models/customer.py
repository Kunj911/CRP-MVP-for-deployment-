"""
app/models/customer.py

Represents a buyer company (the B2B customer receiving spice exports).
A Customer can have many Orders and many Users (customer-side logins).

SQL reference: customers table
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Text, func, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.user import User


class Customer(Base):
    __tablename__ = "customers"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        "customer_id", primary_key=True, autoincrement=True
    )

    # ── Company info ──────────────────────────────────────────────────────────
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_person: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # ── Contact ───────────────────────────────────────────────────────────────
    email: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # ── Location ──────────────────────────────────────────────────────────────
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Quotas ────────────────────────────────────────────────────────────────
    # Default quota is 1000 MB (1 GB)
    storage_quota_mb: Mapped[int] = mapped_column(Integer, default=1000, server_default="1000", nullable=False)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    orders: Mapped[List["Order"]] = relationship(
        "Order", back_populates="customer", lazy="select"
    )
    users: Mapped[List["User"]] = relationship(
        "User", back_populates="customer", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Customer id={self.id} company='{self.company_name}'>"
