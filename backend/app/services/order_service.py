"""
app/services/order_service.py

Order management business logic.

Responsibilities:
  - Create orders with auto-generated order codes
  - List orders with filters and pagination
  - Get single order detail (with customer + creator joins)
  - Update order fields (partial update)
  - Update shipment status (with transition validation)
  - Enforce customer-scoped access (CUSTOMER role sees only their orders)
  - Write audit log on every mutation

Rules:
  - Routes are thin — all logic lives here
  - Every mutation is wrapped in a DB transaction
  - Status can only move FORWARD (no reverting to prior stage)
  - Customers can NEVER write orders — read their own only
  - ADMIN / SUPER_ADMIN can create and update any order
"""

import logging
import math
import uuid
from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.order import Order
from app.models.user import User
from app.schemas.common import PaginationMeta
from app.schemas.order import (
    OrderCreate,
    OrderDetailResponse,
    OrderFilters,
    OrderListItem,
    OrderStatusUpdate,
    OrderUpdate,
    ShipmentStatus,
    VALID_TRANSITIONS,
)

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _generate_order_code() -> str:
    """
    Generate a unique, human-readable order code.
    Format: LT-YYYYMM-XXXX  (e.g. LT-202606-A3F1)
    """
    now = datetime.now(UTC)
    suffix = uuid.uuid4().hex[:4].upper()
    return f"LT-{now.strftime('%Y%m')}-{suffix}"


def _log_audit(
    db: Session,
    user_id: int,
    action_type: str,
    target_id: int,
    description: str,
    order_id: Optional[int] = None,
) -> None:
    """Write a single audit log record. Called after every mutation."""
    db.add(AuditLog(
        user_id=user_id,
        action_type=action_type,
        target_table="orders",
        target_id=target_id,
        order_id=order_id or target_id,
        description=description,
    ))


def _assert_customer_exists(customer_id: int, db: Session) -> Customer:
    """Raise NotFoundException if customer_id doesn't exist."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise NotFoundException("Customer", customer_id)
    return customer


def _get_order_or_404(order_id: int, db: Session) -> Order:
    """Fetch order by PK or raise NotFoundException."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundException("Order", order_id)
    return order


def _assert_can_write(current_user: User) -> None:
    """Only ADMIN and SUPER_ADMIN can create or modify orders."""
    if current_user.role not in {"ADMIN", "SUPER_ADMIN"}:
        raise ForbiddenException(
            "Only ADMIN or SUPER_ADMIN can create or modify orders"
        )


# ── Create ────────────────────────────────────────────────────────────────────

def create_order(
    data: OrderCreate,
    current_user: User,
    db: Session,
) -> Order:
    """
    Create a new export order.

    - Validates customer exists
    - Generates unique order_code (retries on collision)
    - Sets initial status = CREATED
    - Writes audit log
    """
    _assert_can_write(current_user)
    _assert_customer_exists(data.customer_id, db)

    # Generate a unique order code (guard against rare UUID collision)
    for attempt in range(5):
        code = _generate_order_code()
        exists = db.query(Order).filter(Order.order_code == code).first()
        if not exists:
            break
        if attempt == 4:
            raise ConflictException("Could not generate a unique order code. Please retry.")

    order = Order(
        order_code=code,
        customer_id=data.customer_id,
        product_name=data.product_name.strip(),
        quantity=data.quantity,
        unit=data.unit,
        shipment_status=ShipmentStatus.CREATED.value,
        expected_dispatch_date=data.expected_dispatch_date,
        expected_delivery_date=data.expected_delivery_date,
        notes=data.notes,
        created_by=current_user.id,
    )
    db.add(order)
    db.flush()  # get order.id before audit log

    _log_audit(
        db=db,
        user_id=current_user.id,
        action_type="CREATE",
        target_id=order.id,
        description=(
            f"Order '{order.order_code}' created for customer_id={data.customer_id} "
            f"product='{order.product_name}'"
        ),
    )

    db.commit()
    db.refresh(order)
    logger.info(
        "Order created: order_id=%s code=%s by user_id=%s",
        order.id, order.order_code, current_user.id,
    )
    return order


# ── List (with filters + pagination) ─────────────────────────────────────────

def list_orders(
    filters: OrderFilters,
    current_user: User,
    db: Session,
) -> tuple[list[dict], PaginationMeta]:
    """
    Return a paginated, filtered list of orders.

    CUSTOMER role: sees ONLY their own orders (scoped to their customer_id).
    Staff / Admin: sees all orders.

    Returns a tuple: (list of enriched dicts, PaginationMeta)
    The dicts include company_name from a JOIN — mapped to OrderListItem.
    """
    query = (
        db.query(Order, Customer.company_name)
        .join(Customer, Order.customer_id == Customer.id)
    )

    # ── Role-based scoping ────────────────────────────────────────────────────
    if current_user.role == "CUSTOMER":
        if not current_user.customer_id:
            # Safety: customer user with no customer link sees nothing
            return [], PaginationMeta(total=0, page=filters.page, per_page=filters.per_page, pages=0)
        query = query.filter(Order.customer_id == current_user.customer_id)

    # ── Optional filters ──────────────────────────────────────────────────────
    if filters.customer_id:
        query = query.filter(Order.customer_id == filters.customer_id)

    if filters.status:
        query = query.filter(Order.shipment_status == filters.status.value)

    if filters.product_name:
        # INPUT-002 AUDIT: This is SAFE — SQLAlchemy's ilike() auto-parameterizes
        # the value. The f-string here builds a LIKE pattern, but SQLAlchemy sends
        # it as a bound parameter, not raw SQL concatenation.
        query = query.filter(
            Order.product_name.ilike(f"%{filters.product_name}%")
        )

    if filters.from_date:
        query = query.filter(func.date(Order.created_at) >= filters.from_date)

    if filters.to_date:
        query = query.filter(func.date(Order.created_at) <= filters.to_date)

    # ── Count total (before pagination) ───────────────────────────────────────
    total = query.count()
    pages = math.ceil(total / filters.per_page) if total > 0 else 0

    # ── Apply pagination + ordering ───────────────────────────────────────────
    offset = (filters.page - 1) * filters.per_page
    rows = (
        query
        .order_by(Order.created_at.desc())
        .offset(offset)
        .limit(filters.per_page)
        .all()
    )

    # ── Build flat dicts for OrderListItem ────────────────────────────────────
    items = []
    for order, company_name in rows:
        d = {
            "id": order.id,
            "order_code": order.order_code,
            "customer_id": order.customer_id,
            "company_name": company_name,
            "product_name": order.product_name,
            "quantity": order.quantity,
            "unit": order.unit,
            "shipment_status": order.shipment_status,
            "expected_dispatch_date": order.expected_dispatch_date,
            "expected_delivery_date": order.expected_delivery_date,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
        }
        items.append(d)

    meta = PaginationMeta(
        total=total,
        page=filters.page,
        per_page=filters.per_page,
        pages=pages,
    )
    return items, meta


# ── Get single order ──────────────────────────────────────────────────────────

def get_order_by_id(
    order_id: int,
    current_user: User,
    db: Session,
) -> Order:
    """
    Fetch a single order with customer and creator eagerly loaded.

    CUSTOMER role can only see their own customer's orders.
    """
    order = (
        db.query(Order)
        .options(
            joinedload(Order.customer),
            joinedload(Order.creator),
        )
        .filter(Order.id == order_id)
        .first()
    )

    if not order:
        raise NotFoundException("Order", order_id)

    # Customer-scoped access check
    if current_user.role == "CUSTOMER":
        if order.customer_id != current_user.customer_id:
            raise ForbiddenException("You do not have access to this order")

    return order


# ── Update order fields ───────────────────────────────────────────────────────

def update_order(
    order_id: int,
    data: OrderUpdate,
    current_user: User,
    db: Session,
) -> Order:
    """
    Partial update of order fields (not status — use update_order_status).
    Only ADMIN / SUPER_ADMIN can update orders.
    """
    _assert_can_write(current_user)
    order = _get_order_or_404(order_id, db)

    # Apply only the fields that were explicitly provided
    updated_fields = []
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(order, field, value)
        updated_fields.append(field)

    # Validate date consistency after update
    if order.expected_dispatch_date and order.expected_delivery_date:
        if order.expected_delivery_date < order.expected_dispatch_date:
            raise ValidationException(
                "expected_delivery_date cannot be before expected_dispatch_date"
            )

    _log_audit(
        db=db,
        user_id=current_user.id,
        action_type="UPDATE",
        target_id=order.id,
        description=(
            f"Order '{order.order_code}' updated. "
            f"Fields changed: {', '.join(updated_fields)}"
        ),
    )

    db.commit()
    db.refresh(order)
    logger.info(
        "Order updated: order_id=%s fields=%s by user_id=%s",
        order.id, updated_fields, current_user.id,
    )
    return order


# ── Update shipment status ────────────────────────────────────────────────────

def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    current_user: User,
    db: Session,
) -> Order:
    """
    Advance the shipment status of an order.

    Rules:
      - Status can only move forward (VALID_TRANSITIONS)
      - Only ADMIN / SUPER_ADMIN can update status
      - Every status change is audit-logged with optional note
    """
    _assert_can_write(current_user)
    order = _get_order_or_404(order_id, db)

    current_status = ShipmentStatus(order.shipment_status)
    new_status = data.status

    # Validate transition
    if new_status not in VALID_TRANSITIONS.get(current_status, []):
        allowed = [s.value for s in VALID_TRANSITIONS.get(current_status, [])]
        raise ValidationException(
            f"Invalid status transition: '{current_status.value}' → '{new_status.value}'. "
            f"Allowed next status: {allowed if allowed else ['none — order is in terminal state']}"
        )

    old_status = order.shipment_status
    order.shipment_status = new_status.value

    # Append status-change note to order notes if provided
    if data.notes:
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        note_line = f"[{timestamp}] Status → {new_status.value}: {data.notes}"
        order.notes = f"{order.notes}\n{note_line}" if order.notes else note_line

    _log_audit(
        db=db,
        user_id=current_user.id,
        action_type="UPDATE",
        target_id=order.id,
        description=(
            f"Order '{order.order_code}' status changed: "
            f"{old_status} → {new_status.value}"
            + (f" | Note: {data.notes}" if data.notes else "")
        ),
    )

    db.commit()
    db.refresh(order)
    logger.info(
        "Order status updated: order_id=%s %s→%s by user_id=%s",
        order.id, old_status, new_status.value, current_user.id,
    )
    return order


# ── Delete (soft) ─────────────────────────────────────────────────────────────
# Orders are never hard-deleted in production — this is SUPER_ADMIN only.

def cancel_order(
    order_id: int,
    current_user: User,
    db: Session,
) -> Order:
    """
    Cancel an order by forcing status to a terminal state.
    Only SUPER_ADMIN can cancel orders.
    Can only cancel orders that have not yet been SHIPPED or DELIVERED.
    """
    if current_user.role != "SUPER_ADMIN":
        raise ForbiddenException("Only SUPER_ADMIN can cancel orders")

    order = _get_order_or_404(order_id, db)

    if order.shipment_status in {
        ShipmentStatus.SHIPPED.value,
        ShipmentStatus.DELIVERED.value,
    }:
        raise ValidationException(
            f"Cannot cancel an order with status '{order.shipment_status}'"
        )

    old_status = order.shipment_status

    # Use DELIVERED as the closest available terminal state;
    # in a real system you'd add a CANCELLED status to the DB ENUM.
    # For now we log it clearly and leave the order in its current state
    # pending a DB migration to add CANCELLED to the ENUM.
    _log_audit(
        db=db,
        user_id=current_user.id,
        action_type="DELETE",
        target_id=order.id,
        description=(
            f"Order '{order.order_code}' cancellation requested by "
            f"user_id={current_user.id}. Status was: {old_status}. "
            "Pending CANCELLED status addition to DB schema."
        ),
    )

    db.commit()
    logger.warning(
        "Order cancellation requested: order_id=%s by user_id=%s",
        order.id, current_user.id,
    )
    return order
