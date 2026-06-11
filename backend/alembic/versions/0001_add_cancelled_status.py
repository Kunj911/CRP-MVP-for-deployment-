"""Add CANCELLED to shipment_status_enum

Revision ID: 0001
Revises: 
Create Date: 2026-06-10 23:55:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE orders "
        "MODIFY COLUMN shipment_status "
        "ENUM('CREATED','PROCUREMENT','QA_TESTING','PACKAGING','DOCUMENTATION',"
        "'READY_FOR_SHIPMENT','SHIPPED','DELIVERED','CANCELLED') "
        "NOT NULL DEFAULT 'CREATED'"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE orders "
        "MODIFY COLUMN shipment_status "
        "ENUM('CREATED','PROCUREMENT','QA_TESTING','PACKAGING','DOCUMENTATION',"
        "'READY_FOR_SHIPMENT','SHIPPED','DELIVERED') "
        "NOT NULL DEFAULT 'CREATED'"
    )
