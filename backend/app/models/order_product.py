from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.order import Order


class OrderProduct(Base):
    __tablename__ = "order_products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False
    )
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    order: Mapped["Order"] = relationship("Order", back_populates="products")

    def __repr__(self) -> str:
        return (
            f"<OrderProduct id={self.id} "
            f"product='{self.product_name}' order_id={self.order_id}>"
        )
