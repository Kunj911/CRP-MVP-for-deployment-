"""Add order_products table

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-17 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "order_products",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_name", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=True),
        sa.Column("unit", sa.String(20), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(),
            server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_products")),
    )
    op.create_index(
        op.f("ix_order_products_order_id"), "order_products",
        ["order_id"], unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_order_products_order_id"), table_name="order_products")
    op.drop_table("order_products")
