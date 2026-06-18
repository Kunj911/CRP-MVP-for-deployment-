"""
app/api/v1/milestones.py

Milestone tracking and timeline route handlers.
All business logic lives in app/services/milestone_service.py.

Endpoints:
  GET    /api/v1/orders/{order_id}/milestones        → list all milestones for order
  POST   /api/v1/orders/{order_id}/milestones        → create single milestone
  POST   /api/v1/orders/{order_id}/milestones/bulk   → initialize all 9 stages at once
  PATCH  /api/v1/milestones/{milestone_id}           → update milestone status
  GET    /api/v1/orders/{order_id}/timeline          → full ordered timeline

Access matrix:
  ┌───────────────────────────────┬──────────────────────────────┬──────────┐
  │ Action                        │ Staff                        │ Customer │
  ├───────────────────────────────┼──────────────────────────────┼──────────┤
  │ List milestones               │ All                          │ Read own │
  │ Create milestone              │ ADMIN, WAREHOUSE, QA, DOCS   │ ✗        │
  │ Bulk init                     │ ADMIN only                   │ ✗        │
  │ Update status                 │ ADMIN, WAREHOUSE, QA, DOCS   │ ✗        │
  │ Get timeline                  │ All                          │ Read own │
  └───────────────────────────────┴──────────────────────────────┴──────────┘
"""

import logging
from typing import List

from fastapi import APIRouter

from app.api.deps import AdminUser, CurrentUser, DbSession, WarehouseUser
from app.core.exceptions import ForbiddenException
from app.schemas.common import SuccessResponse
from app.schemas.milestone import (
    MilestoneCreate,
    MilestoneResponse,
    MilestoneStatusUpdate,
    OrderTimelineResponse,
)
from app.services import milestone_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Milestones"])


# ── GET /orders/{order_id}/milestones ─────────────────────────────────────────

@router.get(
    "/orders/{order_id}/milestones",
    response_model=SuccessResponse[List[MilestoneResponse]],
    summary="List milestones for an order",
    description=(
        "Returns all milestones for the given order, sorted by the 9-stage sequence. "
        "CUSTOMER role can only access milestones for their own orders."
    ),
)
def list_milestones(
    order_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[List[MilestoneResponse]]:
    # Customer scoping — service enforces order ownership
    _assert_customer_order_access(order_id, current_user, db)

    milestones = milestone_service.get_milestones_for_order(
        order_id=order_id,
        current_user=current_user,
        db=db,
    )
    return SuccessResponse(
        data=milestones,
        message=f"{len(milestones)} milestone(s) found for order {order_id}",
    )


# ── POST /orders/{order_id}/milestones ────────────────────────────────────────

@router.post(
    "/orders/{order_id}/milestones",
    response_model=SuccessResponse[MilestoneResponse],
    status_code=201,
    summary="Create a single milestone",
    description=(
        "Adds a single milestone stage to an order. "
        "Each stage can only exist once per order. "
        "Requires ADMIN, WAREHOUSE, QA, or DOCUMENTATION role."
    ),
)
def create_milestone(
    order_id: int,
    body: MilestoneCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[MilestoneResponse]:
    milestone = milestone_service.create_milestone(
        order_id=order_id,
        data=body,
        current_user=current_user,
        db=db,
    )
    return SuccessResponse(
        data=milestone,
        message=f"Milestone '{milestone.stage_name}' created successfully",
    )


# ── POST /orders/{order_id}/milestones/bulk ───────────────────────────────────

@router.post(
    "/orders/{order_id}/milestones/bulk",
    response_model=SuccessResponse[List[MilestoneResponse]],
    status_code=201,
    summary="Initialize all 9 milestones",
    description=(
        "Creates all 9 milestone stages for an order in one call — all set to PENDING. "
        "Safe to call multiple times: skips stages that already exist. "
        "Requires ADMIN or SUPER_ADMIN role."
    ),
)
def bulk_init_milestones(
    order_id: int,
    current_user: AdminUser,      # Admin-only
    db: DbSession,
) -> SuccessResponse[List[MilestoneResponse]]:
    milestones = milestone_service.initialize_all_milestones(
        order_id=order_id,
        current_user=current_user,
        db=db,
    )
    return SuccessResponse(
        data=milestones,
        message=f"All milestones initialized for order {order_id}. Total: {len(milestones)}",
    )


# ── PATCH /milestones/{milestone_id} ─────────────────────────────────────────

@router.patch(
    "/milestones/{milestone_id}",
    response_model=SuccessResponse[MilestoneResponse],
    summary="Update milestone status",
    description=(
        "Advances a milestone's status: PENDING → IN_PROGRESS → COMPLETED.\n\n"
        "Rules:\n"
        "- Transitions must be forward-only (no reverting)\n"
        "- COMPLETED is a terminal state — cannot be changed\n"
        "- On COMPLETED: timestamps and completer are automatically recorded\n"
        "- Remarks are appended (timestamped), not overwritten\n"
        "- Completing a milestone triggers a customer notification (when notification service is wired)\n\n"
        "Requires ADMIN, WAREHOUSE, QA, or DOCUMENTATION role."
    ),
)
def update_milestone(
    milestone_id: int,
    body: MilestoneStatusUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[MilestoneResponse]:
    milestone = milestone_service.update_milestone_status(
        milestone_id=milestone_id,
        data=body,
        current_user=current_user,
        db=db,
    )
    return SuccessResponse(
        data=milestone,
        message=(
            f"Milestone '{milestone.stage_name}' updated to '{milestone.status}'"
        ),
    )


# ── GET /orders/{order_id}/timeline ──────────────────────────────────────────

@router.get(
    "/orders/{order_id}/timeline",
    response_model=SuccessResponse[OrderTimelineResponse],
    summary="Get full order timeline",
    description=(
        "Returns the complete milestone timeline for an order.\n\n"
        "Response includes:\n"
        "- All milestones sorted by the 9-stage sequence\n"
        "- `overall_progress`: % of completed stages (0–100)\n"
        "- `active_stage`: the current IN_PROGRESS stage\n"
        "- `is_active` / `is_completed` flags per milestone node\n"
        "- `completer`: who completed each milestone\n\n"
        "CUSTOMER role can only view their own orders' timelines."
    ),
)
def get_order_timeline(
    order_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[OrderTimelineResponse]:
    _assert_customer_order_access(order_id, current_user, db)

    timeline = milestone_service.get_order_timeline(
        order_id=order_id,
        current_user=current_user,
        db=db,
    )
    return SuccessResponse(
        data=timeline,
        message=f"Timeline retrieved. Progress: {timeline.overall_progress}%",
    )


# ── POST /orders/{order_id}/complete-stage ─────────────────────────────────────

@router.post(
    "/orders/{order_id}/complete-stage",
    response_model=SuccessResponse[MilestoneResponse],
    summary="Mark current stage complete",
    description=(
        "Finds the current IN_PROGRESS milestone for the order and marks it COMPLETED. "
        "The next pending milestone is automatically advanced to IN_PROGRESS.\n\n"
        "Rules:\n"
        "- Only SUPER_ADMIN, ADMIN, and WAREHOUSE can progress stages\n"
        "- Cannot complete a stage that is already COMPLETED\n"
        "- Cannot skip stages — only the current active stage can be completed\n"
        "- If no stage is active, the first pending stage will be auto-started first\n\n"
        "On completion:\n"
        "- completed_at and completed_by are saved\n"
        "- An OrderEvent is recorded for the timeline\n"
        "- An audit log entry is created\n"
        "- A customer notification is triggered"
    ),
)
def mark_stage_complete(
    order_id: int,
    current_user: WarehouseUser,
    db: DbSession,
) -> SuccessResponse[MilestoneResponse]:
    logger.info("complete-stage: order_id=%s user_id=%s role=%s", order_id, current_user.id, current_user.role)
    try:
        milestone = milestone_service.complete_current_stage(
            order_id=order_id,
            current_user=current_user,
            db=db,
        )
        logger.info("complete-stage OK: order_id=%s milestone_id=%s", order_id, milestone.id)
        return SuccessResponse(
            data=milestone,
            message=f"Stage '{milestone.stage_name}' completed successfully",
        )
    except Exception:
        logger.exception("complete-stage FAILED: order_id=%s", order_id)
        raise


# ── Customer scoping helper ───────────────────────────────────────────────────

def _assert_customer_order_access(
    order_id: int, current_user, db: DbSession
) -> None:
    """
    For CUSTOMER role: verify the order belongs to their customer_id.
    Staff roles pass through without restriction.
    """
    if current_user.role != "CUSTOMER":
        return

    from app.models.order import Order

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("Order", order_id)

    if order.customer_id != current_user.customer_id:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("Order", order_id)
