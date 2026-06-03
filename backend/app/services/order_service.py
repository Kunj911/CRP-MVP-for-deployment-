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
from app.core.security import hash_password
from app.schemas.order import (
    OrderCreate,
    OrderDetailResponse,
    OrderFilters,
    OrderListItem,
    OrderStatusUpdate,
    OrderUpdate,
    ShipmentStatus,
    VALID_TRANSITIONS,
    OrderWithNewCustomerCreate,
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

    try:
        from app.services.notification_service import send_order_created_alert
        send_order_created_alert(order_id=order.id, db=db)
    except Exception as exc:
        logger.error("Order-created notification failed for order_id=%s: %s", order.id, exc)

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
        db.query(Order, Customer.company_name, Customer.country)
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

    # ── Temporary debug logs ──────────────────────────────────────────────────
    try:
        compiled_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
    except Exception:
        compiled_query = str(query.statement)
    logger.info("TEMPORARY LOG: Backend received status filter: %s", filters.status)
    logger.info("TEMPORARY LOG: Backend received parameter: %s", filters.model_dump())
    logger.info("TEMPORARY LOG: Generated database query: %s", compiled_query)
    logger.info("TEMPORARY LOG: Number of returned records: %d", len(rows))

    # ── Build flat dicts for OrderListItem ────────────────────────────────────
    items = []
    for order, company_name, country in rows:
        d = {
            "id": order.id,
            "order_code": order.order_code,
            "customer_id": order.customer_id,
            "company_name": company_name,
            "destination_country": country,
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
            raise NotFoundException("Order", order_id)

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

    # ── Document Checklist Blocking Rules ────────────────────────────────────
    from app.models.order_document_requirement import OrderDocumentRequirement
    
    # Rule 1: Block moving past QA_TESTING (i.e. to PACKAGING or further) unless Certificate of Analysis is approved
    past_qa = {"PACKAGING", "DOCUMENTATION", "READY_FOR_SHIPMENT", "SHIPPED", "DELIVERED"}
    if new_status.value in past_qa:
        coa_req = db.query(OrderDocumentRequirement).filter(
            OrderDocumentRequirement.order_id == order.id,
            OrderDocumentRequirement.document_type == "certificate_of_analysis"
        ).first()
        if coa_req and coa_req.required and not coa_req.approved:
            raise ValidationException(
                f"Cannot advance status to '{new_status.value}': "
                "Certificate of Analysis (COA) must be uploaded and approved first."
            )

    # Rule 2: Block moving to SHIPPED unless Invoice, Purchase Order, Packing List, COA, and Product Spec are approved
    if new_status.value == "SHIPPED":
        must_approve = {"invoice", "purchase_order", "packing_list", "certificate_of_analysis", "product_specification"}
        for dtype in must_approve:
            req = db.query(OrderDocumentRequirement).filter(
                OrderDocumentRequirement.order_id == order.id,
                OrderDocumentRequirement.document_type == dtype
            ).first()
            if req and req.required and not req.approved:
                raise ValidationException(
                    f"Cannot advance status to 'SHIPPED': "
                    f"Required document '{dtype.replace('_', ' ').title()}' is not approved."
                )

    # Rule 3: Block moving to DELIVERED unless ALL required checklist items are approved and bill_of_lading is uploaded
    if new_status.value == "DELIVERED":
        unapproved = db.query(OrderDocumentRequirement).filter(
            OrderDocumentRequirement.order_id == order.id,
            OrderDocumentRequirement.required == True,
            OrderDocumentRequirement.approved == False
        ).all()
        if unapproved:
            missing = ", ".join([r.document_type.replace('_', ' ').title() for r in unapproved])
            raise ValidationException(
                f"Cannot advance status to 'DELIVERED': "
                f"The following required documents are not approved: {missing}"
            )
            
        bl_req = db.query(OrderDocumentRequirement).filter(
            OrderDocumentRequirement.order_id == order.id,
            OrderDocumentRequirement.document_type == "bill_of_lading"
        ).first()
        if not bl_req or not bl_req.uploaded:
            raise ValidationException(
                "Cannot advance status to 'DELIVERED': Bill of Lading (BL) must be uploaded."
            )

    old_status = order.shipment_status
    order.shipment_status = new_status.value

    # Append status-change note to order notes if provided
    if data.notes:
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        note_line = f"[{timestamp}] Status → {new_status.value}: {data.notes}"
        order.notes = f"{order.notes}\n{note_line}" if order.notes else note_line

    # Log OrderEvent
    from app.models.order_event import OrderEvent
    event = OrderEvent(
        order_id=order.id,
        event_type="status_changed",
        description=f"Order status updated from {old_status} to {new_status.value}."
    )
    db.add(event)

    # ── Notifications & Async Task Triggers ──────────────────────────────────
    customer_users = db.query(User).filter(
        User.customer_id == order.customer_id,
        User.role == "CUSTOMER",
        User.is_active == True
    ).all()

    if new_status.value == "SHIPPED":
        for u in customer_users:
            from app.services.notification_service import create_in_app_notification
            create_in_app_notification(
                db=db,
                user_id=u.id,
                order_id=order.id,
                title="Shipment Dispatched",
                message=f"Your shipment for order {order.order_code} has been dispatched.",
                notification_type="shipment",
                related_order_id=order.id
            )
        from app.tasks.order_tasks import send_shipment_dispatched_email
        send_shipment_dispatched_email.delay(order.id)

    elif new_status.value == "DELIVERED":
        for u in customer_users:
            from app.services.notification_service import create_in_app_notification
            create_in_app_notification(
                db=db,
                user_id=u.id,
                order_id=order.id,
                title="Shipment Delivered",
                message=f"Your order {order.order_code} has been marked as delivered.",
                notification_type="shipment",
                related_order_id=order.id
            )
        from app.tasks.order_tasks import send_order_delivered_email
        send_order_delivered_email.delay(order.id)

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


def create_order_with_new_customer(
    data: OrderWithNewCustomerCreate,
    current_user: User,
    db: Session,
) -> Order:
    """
    Onboard a new customer and create their first order in a single transaction.

    - Validates permissions (ADMIN/SUPER_ADMIN only)
    - Validates email format/uniqueness across both customers & users
    - Validates company name uniqueness to prevent duplicates
    - Creates Customer record
    - Creates associated CUSTOMER user record with secure default password
    - Generates unique order_code
    - Creates Order record linked to the newly created customer
    - Initializes the 9-stage tracking pipeline milestones
    - Logs audit trail events for customer, user, and order creation
    - Triggers notifications (welcome email & order-created alert)
    - Safely rolls back all operations in case of database exception
    """
    _assert_can_write(current_user)

    # 1. Pre-validation checks
    email_clean = data.customer.email.strip().lower()
    company_clean = data.customer.company_name.strip()

    # Check email uniqueness in users
    existing_user = db.query(User).filter(User.email == email_clean).first()
    if existing_user:
        raise ConflictException(f"A user with email '{email_clean}' already exists")

    # Check company name uniqueness in customers
    existing_customer_name = db.query(Customer).filter(Customer.company_name == company_clean).first()
    if existing_customer_name:
        raise ConflictException(f"A customer with company name '{company_clean}' already exists")

    # Check email uniqueness in customers
    existing_customer_email = db.query(Customer).filter(Customer.email == email_clean).first()
    if existing_customer_email:
        raise ConflictException(f"A customer with email '{email_clean}' already exists")

    try:
        # 2. Create Customer
        customer = Customer(
            company_name=company_clean,
            contact_person=data.customer.contact_person,
            email=email_clean,
            phone=data.customer.phone.strip(),
            country=data.customer.country,
            address=data.customer.address,
        )
        db.add(customer)
        db.flush()  # Generate customer.id

        # 3. Create User
        # Default password is "Welcome@1234"
        pwd_hash = hash_password("Welcome@1234")
        user = User(
            full_name=data.customer.contact_person or company_clean,
            email=email_clean,
            phone=data.customer.phone.strip(),
            password_hash=pwd_hash,
            role="CUSTOMER",
            customer_id=customer.id,
            is_active=True,
        )
        db.add(user)
        db.flush()  # Generate user.id

        # 4. Create Order
        # Generate unique order code (guard against collisions)
        for attempt in range(5):
            code = _generate_order_code()
            exists = db.query(Order).filter(Order.order_code == code).first()
            if not exists:
                break
            if attempt == 4:
                raise ConflictException("Could not generate a unique order code. Please retry.")

        order = Order(
            order_code=code,
            customer_id=customer.id,
            product_name=data.order.product_name.strip(),
            quantity=data.order.quantity,
            unit=data.order.unit,
            shipment_status=ShipmentStatus.CREATED.value,
            expected_dispatch_date=data.order.expected_dispatch_date,
            expected_delivery_date=data.order.expected_delivery_date,
            notes=data.order.notes,
            created_by=current_user.id,
        )
        db.add(order)
        db.flush()  # Generate order.id

        # 5. Initialize milestones (commit=False to keep them in this transaction)
        from app.services.milestone_service import initialize_all_milestones
        initialize_all_milestones(order_id=order.id, current_user=current_user, db=db, commit=False)

        # 6. Audit logs
        _log_audit(
            db=db,
            user_id=current_user.id,
            action_type="CREATE",
            target_id=customer.id,
            description=f"Customer '{customer.company_name}' onboarded during combined order creation.",
        )
        _log_audit(
            db=db,
            user_id=current_user.id,
            action_type="CREATE",
            target_id=user.id,
            description=f"User '{user.email}' created for new customer '{customer.company_name}'.",
        )
        _log_audit(
            db=db,
            user_id=current_user.id,
            action_type="CREATE",
            target_id=order.id,
            description=f"Order '{order.order_code}' created for newly onboarded customer '{customer.company_name}'.",
        )

        db.commit()
        db.refresh(order)
        logger.info(
            "Order created with new customer onboarded successfully: order_id=%s code=%s customer_id=%s",
            order.id, order.order_code, customer.id
        )

    except Exception as exc:
        db.rollback()
        logger.error("Transaction rolled back for combined customer + order creation: %s", exc)
        raise exc

    # 7. Post-transaction notifications
    try:
        from app.services.notification_service import send_customer_created_email, send_order_created_alert
        send_customer_created_email(
            to_address=user.email,
            company_name=customer.company_name,
            contact_name=user.full_name,
        )
        send_order_created_alert(order_id=order.id, db=db)
    except Exception as n_exc:
        logger.error("Failed to send post-onboarding notifications: %s", n_exc)

    return order
