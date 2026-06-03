"""
app/api/v1/orders.py

Order management route handlers — thin HTTP layer only.
All business logic lives in app/services/order_service.py.

Endpoints:
  GET    /api/v1/orders                      → list orders (paginated, filtered)
  POST   /api/v1/orders                      → create order
  GET    /api/v1/orders/{order_id}           → order detail with customer info
  PATCH  /api/v1/orders/{order_id}           → update order fields
  PATCH  /api/v1/orders/{order_id}/status    → advance shipment status
  DELETE /api/v1/orders/{order_id}/cancel    → cancel order (SUPER_ADMIN only)

Access matrix (enforced in service layer):
  ┌─────────────────────────────────────┬────────────┬──────────┐
  │ Action                              │ Staff      │ Customer │
  ├─────────────────────────────────────┼────────────┼──────────┤
  │ List orders                         │ All        │ Own only │
  │ Create order                        │ ADMIN only │ ✗        │
  │ Get order detail                    │ Any staff  │ Own only │
  │ Update fields / status              │ ADMIN only │ ✗        │
  │ Cancel                              │ SUPER_ADMIN│ ✗        │
  └─────────────────────────────────────┴────────────┴──────────┘
"""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.schemas.order import (
    OrderCreate,
    OrderDetailResponse,
    OrderFilters,
    OrderListItem,
    OrderResponse,
    OrderStatusUpdate,
    OrderUpdate,
    ShipmentStatus,
    OrderWithNewCustomerCreate,
)
from app.services import order_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["Orders"])


# ── GET /orders ───────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=PaginatedResponse[OrderListItem],
    summary="List orders",
    description=(
        "Returns a paginated list of orders. "
        "Supports filtering by customer, status, product name, and date range. "
        "CUSTOMER role only sees their own company's orders."
    ),
)
def list_orders(
    current_user: CurrentUser,
    db: DbSession,
    # Filters as individual query params (Pydantic model as Depends)
    customer_id: Optional[int] = Query(None, gt=0, description="Filter by customer ID"),
    status: Optional[ShipmentStatus] = Query(None, description="Filter by shipment status"),
    product_name: Optional[str] = Query(None, max_length=200, description="Partial product name search"),
    from_date: Optional[str] = Query(None, description="Created on or after (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="Created on or before (YYYY-MM-DD)"),
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> PaginatedResponse[OrderListItem]:

    # Parse optional date strings
    from datetime import date as date_type
    parsed_from = date_type.fromisoformat(from_date) if from_date else None
    parsed_to = date_type.fromisoformat(to_date) if to_date else None

    filters = OrderFilters(
        customer_id=customer_id,
        status=status,
        product_name=product_name,
        from_date=parsed_from,
        to_date=parsed_to,
        page=page,
        per_page=per_page,
    )

    items, meta = order_service.list_orders(
        filters=filters,
        current_user=current_user,
        db=db,
    )

    return PaginatedResponse(
        data=[OrderListItem(**item) for item in items],
        meta=meta,
    )


# ── POST /orders ──────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=SuccessResponse[OrderResponse],
    status_code=201,
    summary="Create a new order",
    description=(
        "Creates a new export order. "
        "Requires ADMIN or SUPER_ADMIN role. "
        "Automatically generates a unique order code (LT-YYYYMM-XXXX format). "
        "Initial status is always CREATED."
    ),
)
def create_order(
    body: OrderCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[OrderResponse]:
    order = order_service.create_order(
        data=body,
        current_user=current_user,
        db=db,
    )
    return SuccessResponse(
        data=OrderResponse.model_validate(order),
        message=f"Order '{order.order_code}' created successfully",
    )


# ── POST /orders/with-new-customer ─────────────────────────────────────────────

@router.post(
    "/with-new-customer",
    response_model=SuccessResponse[OrderResponse],
    status_code=201,
    summary="Create an order with a new customer",
    description=(
        "Onboards a new customer profile and maps their first order within a single transaction. "
        "Requires ADMIN or SUPER_ADMIN role."
    ),
)
def create_order_with_new_customer(
    body: OrderWithNewCustomerCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[OrderResponse]:
    order = order_service.create_order_with_new_customer(
        data=body,
        current_user=current_user,
        db=db,
    )
    return SuccessResponse(
        data=OrderResponse.model_validate(order),
        message=f"Order '{order.order_code}' for new customer created successfully",
    )


# ── GET /orders/dashboard/stats ───────────────────────────────────────────────

@router.get(
    "/dashboard/stats",
    summary="Get admin dashboard statistics",
    description="Retrieve statistics for documents, orders, pending reviews, and missing documents."
)
def get_dashboard_stats(
    current_user: CurrentUser,
    db: DbSession,
):
    from app.core.exceptions import ForbiddenException
    if current_user.role not in {"SUPER_ADMIN", "ADMIN", "QA", "DOCUMENTATION", "WAREHOUSE"}:
        raise ForbiddenException("Only staff users can access dashboard statistics")

    from app.models.order import Order
    from app.models.document import Document
    from app.models.order_document_requirement import OrderDocumentRequirement
    from datetime import datetime, time, date

    # 1. Active orders (eager load customer relationship)
    from sqlalchemy.orm import joinedload
    active_orders = (
        db.query(Order)
        .options(joinedload(Order.customer))
        .filter(Order.shipment_status.notin_(["DELIVERED", "CANCELLED"]))
        .all()
    )
    active_count = len(active_orders)

    # 2. Dispatched orders
    dispatched_count = db.query(Order).filter(Order.shipment_status.in_(["SHIPPED", "SHIPMENT_DISPATCHED"])).count()

    # 3. Documents uploaded today
    today_start = datetime.combine(date.today(), time.min)
    docs_today_count = db.query(Document).filter(
        Document.uploaded_at >= today_start,
        Document.is_deleted == False
    ).count()

    # 4. Pending reviews count
    pending_reviews_count = db.query(Document).filter(
        Document.status.in_(["uploaded", "under_review"]),
        Document.is_deleted == False
    ).count()

    # 5. Orders missing required documents (batch query to avoid N+1 loop)
    missing_docs_orders = []
    active_order_ids = [o.id for o in active_orders]
    requirements_by_order = {}
    if active_order_ids:
        all_reqs = (
            db.query(OrderDocumentRequirement)
            .filter(
                OrderDocumentRequirement.order_id.in_(active_order_ids),
                OrderDocumentRequirement.required == True,
                OrderDocumentRequirement.approved == False
            )
            .all()
        )
        for req in all_reqs:
            requirements_by_order.setdefault(req.order_id, []).append(req.document_type)

    for order in active_orders:
        missing_types = requirements_by_order.get(order.id, [])
        if missing_types:
            customer_name = order.customer.company_name if order.customer else "Unknown"
            missing_docs_orders.append({
                "order_id": order.id,
                "order_code": order.order_code,
                "customer_name": customer_name,
                "status": order.shipment_status,
                "missing_documents": missing_types
            })


    return {
        "status": "success",
        "data": {
            "active_orders_count": active_count,
            "dispatched_orders_count": dispatched_count,
            "docs_uploaded_today": docs_today_count,
            "pending_reviews_count": pending_reviews_count,
            "orders_missing_required_documents": missing_docs_orders
        }
    }


# ── GET /orders/{order_id} ────────────────────────────────────────────────────

@router.get(
    "/{order_id}",
    response_model=SuccessResponse[OrderDetailResponse],
    summary="Get order detail",
    description=(
        "Returns full order details including nested customer and creator info. "
        "CUSTOMER role can only access their own company's orders."
    ),
)
def get_order(
    order_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[OrderDetailResponse]:
    order = order_service.get_order_by_id(
        order_id=order_id,
        current_user=current_user,
        db=db,
    )
    return SuccessResponse(
        data=OrderDetailResponse.model_validate(order),
        message="OK",
    )


# ── PATCH /orders/{order_id} ──────────────────────────────────────────────────

@router.patch(
    "/{order_id}",
    response_model=SuccessResponse[OrderResponse],
    summary="Update order fields",
    description=(
        "Partial update of order fields: product, quantity, unit, dates, notes. "
        "Does NOT update shipment status — use the /status endpoint for that. "
        "Requires ADMIN or SUPER_ADMIN role."
    ),
)
def update_order(
    order_id: int,
    body: OrderUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[OrderResponse]:
    order = order_service.update_order(
        order_id=order_id,
        data=body,
        current_user=current_user,
        db=db,
    )
    return SuccessResponse(
        data=OrderResponse.model_validate(order),
        message=f"Order '{order.order_code}' updated successfully",
    )


# ── PATCH /orders/{order_id}/status ──────────────────────────────────────────

@router.patch(
    "/{order_id}/status",
    response_model=SuccessResponse[OrderResponse],
    summary="Advance shipment status",
    description=(
        "Moves the order to the next shipment status stage. "
        "Only valid forward transitions are accepted — see the status flow:\n\n"
        "CREATED → PROCUREMENT → QA_TESTING → PACKAGING → "
        "DOCUMENTATION → READY_FOR_SHIPMENT → SHIPPED → DELIVERED\n\n"
        "Requires ADMIN or SUPER_ADMIN role."
    ),
)
def update_status(
    order_id: int,
    body: OrderStatusUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[OrderResponse]:
    order = order_service.update_order_status(
        order_id=order_id,
        data=body,
        current_user=current_user,
        db=db,
    )
    return SuccessResponse(
        data=OrderResponse.model_validate(order),
        message=f"Order '{order.order_code}' status updated to '{order.shipment_status}'",
    )


# ── DELETE /orders/{order_id}/cancel ─────────────────────────────────────────

@router.delete(
    "/{order_id}/cancel",
    response_model=SuccessResponse[str],
    summary="Cancel an order",
    description=(
        "Cancels an order. Only available to SUPER_ADMIN. "
        "Cannot cancel orders that are already SHIPPED or DELIVERED. "
        "Note: A CANCELLED status will be added to the DB ENUM in the next migration."
    ),
)
def cancel_order(
    order_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[str]:
    order = order_service.cancel_order(
        order_id=order_id,
        current_user=current_user,
        db=db,
    )
    return SuccessResponse(
        data=order.order_code,
        message=f"Order '{order.order_code}' cancellation has been logged",
    )
