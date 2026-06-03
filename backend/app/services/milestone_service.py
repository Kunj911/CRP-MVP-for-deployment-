"""
app/services/milestone_service.py

Milestone tracking and timeline business logic.

Responsibilities:
  - Create individual milestones for an order
  - Bulk-initialize all 9 stages as PENDING in one call
  - Update milestone status (PENDING → IN_PROGRESS → COMPLETED)
  - Build the full ordered timeline response for an order
  - Enforce no-duplicate stage rule per order
  - Enforce status transition rules (no skipping, no reverting)
  - Audit log every state change
  - Trigger notification hook on COMPLETED (notification_service stub)

Access rules:
  - CUSTOMER: read-only (no create/update)
  - WAREHOUSE: can create + update milestones
  - QA: can create + update milestones
  - DOCUMENTATION: can create + update milestones
  - ADMIN / SUPER_ADMIN: full access
"""

import logging
from datetime import datetime, UTC
from typing import List, Optional

from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.models.audit_log import AuditLog
from app.models.milestone import Milestone
from app.models.order import Order
from app.models.user import User
from app.schemas.milestone import (
    STAGE_LABELS,
    STAGE_SEQUENCE,
    CompleterInfo,
    MilestoneCreate,
    MilestoneResponse,
    MilestoneStage,
    MilestoneStatus,
    MilestoneStatusUpdate,
    MilestoneTimelineItem,
    OrderTimelineResponse,
)

logger = logging.getLogger(__name__)

# ── Roles allowed to write milestones ─────────────────────────────────────────
_WRITE_ROLES = {"SUPER_ADMIN", "ADMIN", "WAREHOUSE", "QA", "DOCUMENTATION"}

# ── Status transition rules ───────────────────────────────────────────────────
_VALID_STATUS_TRANSITIONS: dict[MilestoneStatus, list[MilestoneStatus]] = {
    MilestoneStatus.PENDING:     [MilestoneStatus.IN_PROGRESS],
    MilestoneStatus.IN_PROGRESS: [MilestoneStatus.COMPLETED],
    MilestoneStatus.COMPLETED:   [],   # terminal — cannot revert
}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _assert_can_write(current_user: User) -> None:
    if current_user.role not in _WRITE_ROLES:
        raise ForbiddenException(
            "Only internal staff (ADMIN, WAREHOUSE, QA, DOCUMENTATION) "
            "can create or update milestones"
        )


def _get_order_or_404(order_id: int, db: Session) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundException("Order", order_id)
    return order


def _get_milestone_or_404(milestone_id: int, db: Session) -> Milestone:
    milestone = (
        db.query(Milestone)
        .options(joinedload(Milestone.completer))
        .filter(Milestone.id == milestone_id)
        .first()
    )
    if not milestone:
        raise NotFoundException("Milestone", milestone_id)
    return milestone


def _to_response(milestone: Milestone) -> MilestoneResponse:
    """Convert ORM Milestone to MilestoneResponse, injecting stage_label."""
    stage = MilestoneStage(milestone.stage_name)
    return MilestoneResponse(
        id=milestone.id,
        order_id=milestone.order_id,
        stage_name=stage,
        stage_label=STAGE_LABELS[stage],
        status=MilestoneStatus(milestone.status),
        remarks=milestone.remarks,
        completed_by=milestone.completed_by,
        completed_at=milestone.completed_at,
        created_at=milestone.created_at,
    )


def _to_timeline_item(milestone: Milestone) -> MilestoneTimelineItem:
    """Convert ORM Milestone to a full timeline node."""
    stage = MilestoneStage(milestone.stage_name)
    status = MilestoneStatus(milestone.status)
    stage_index = STAGE_SEQUENCE.index(stage) if stage in STAGE_SEQUENCE else -1

    completer_info: Optional[CompleterInfo] = None
    if milestone.completer:
        completer_info = CompleterInfo(
            id=milestone.completer.id,
            full_name=milestone.completer.full_name,
            role=milestone.completer.role,
        )

    return MilestoneTimelineItem(
        id=milestone.id,
        order_id=milestone.order_id,
        stage_name=stage,
        stage_label=STAGE_LABELS[stage],
        stage_index=stage_index,
        status=status,
        is_active=status == MilestoneStatus.IN_PROGRESS,
        is_completed=status == MilestoneStatus.COMPLETED,
        remarks=milestone.remarks,
        completed_at=milestone.completed_at,
        created_at=milestone.created_at,
        completer=completer_info,
    )


def _log_audit(
    db: Session,
    user_id: int,
    action_type: str,
    target_id: int,
    order_id: int,
    description: str,
) -> None:
    db.add(AuditLog(
        user_id=user_id,
        action_type=action_type,
        target_table="milestones",
        target_id=target_id,
        order_id=order_id,
        description=description,
    ))


# ── Create single milestone ───────────────────────────────────────────────────

def create_milestone(
    order_id: int,
    data: MilestoneCreate,
    current_user: User,
    db: Session,
) -> MilestoneResponse:
    """
    Create a single milestone for an order.

    Rules:
      - Order must exist
      - Same stage_name cannot exist twice for the same order
      - Only staff roles can create
    """
    _assert_can_write(current_user)
    _get_order_or_404(order_id, db)

    # Duplicate stage guard
    existing = db.query(Milestone).filter(
        Milestone.order_id == order_id,
        Milestone.stage_name == data.stage_name.value,
    ).first()
    if existing:
        raise ConflictException(
            f"Milestone '{data.stage_name.value}' already exists for order {order_id}"
        )

    milestone = Milestone(
        order_id=order_id,
        stage_name=data.stage_name.value,
        status=MilestoneStatus.PENDING.value,
        remarks=data.remarks,
    )
    db.add(milestone)
    db.flush()

    _log_audit(
        db=db,
        user_id=current_user.id,
        action_type="CREATE",
        target_id=milestone.id,
        order_id=order_id,
        description=(
            f"Milestone '{data.stage_name.value}' created for order_id={order_id}"
        ),
    )

    db.commit()
    db.refresh(milestone)
    logger.info(
        "Milestone created: milestone_id=%s stage=%s order_id=%s",
        milestone.id, data.stage_name.value, order_id,
    )
    return _to_response(milestone)


# ── Bulk initialize all 9 milestones ─────────────────────────────────────────

def initialize_all_milestones(
    order_id: int,
    current_user: User,
    db: Session,
    commit: bool = True,
) -> List[MilestoneResponse]:
    """
    Create all 9 milestone stages for an order in sequence, all PENDING.

    Skips any stages that already exist (idempotent — safe to call multiple times).
    Called automatically when an order is created (optional).
    """
    _assert_can_write(current_user)
    _get_order_or_404(order_id, db)

    # Find which stages already exist
    existing_stages = {
        row.stage_name
        for row in db.query(Milestone.stage_name)
        .filter(Milestone.order_id == order_id)
        .all()
    }

    created = []
    for stage in STAGE_SEQUENCE:
        if stage.value in existing_stages:
            continue  # skip already-existing stages

        milestone = Milestone(
            order_id=order_id,
            stage_name=stage.value,
            status=MilestoneStatus.PENDING.value,
        )
        db.add(milestone)
        created.append(milestone)

    if created:
        db.flush()
        for m in created:
            _log_audit(
                db=db,
                user_id=current_user.id,
                action_type="CREATE",
                target_id=m.id,
                order_id=order_id,
                description=f"Bulk init: milestone '{m.stage_name}' created for order_id={order_id}",
            )

    if commit:
        db.commit()
    else:
        db.flush()

    # Return all milestones for the order in stage sequence
    return get_milestones_for_order(order_id=order_id, current_user=current_user, db=db)


# ── Get all milestones for an order ──────────────────────────────────────────

def get_milestones_for_order(
    order_id: int,
    current_user: User,
    db: Session,
) -> List[MilestoneResponse]:
    """
    Return all milestones for an order, sorted by STAGE_SEQUENCE order.
    Customers can access (read-only) — scoped check done by calling route.
    """
    _get_order_or_404(order_id, db)

    milestones = (
        db.query(Milestone)
        .options(joinedload(Milestone.completer))
        .filter(Milestone.order_id == order_id)
        .all()
    )

    # Sort by stage sequence index
    stage_order = {stage.value: i for i, stage in enumerate(STAGE_SEQUENCE)}
    milestones.sort(key=lambda m: stage_order.get(m.stage_name, 99))

    return [_to_response(m) for m in milestones]


# ── Update milestone status ───────────────────────────────────────────────────

def update_milestone_status(
    milestone_id: int,
    data: MilestoneStatusUpdate,
    current_user: User,
    db: Session,
) -> MilestoneResponse:
    """
    Advance a milestone's status.

    Transition rules:
      PENDING → IN_PROGRESS → COMPLETED

    On COMPLETED:
      - Sets completed_by = current_user.id
      - Sets completed_at = now
      - Triggers notification hook (stubbed — notification_service.send_milestone_alert)

    On status update:
      - Remarks are APPENDED (not replaced) if provided
    """
    _assert_can_write(current_user)
    milestone = _get_milestone_or_404(milestone_id, db)

    current_status = MilestoneStatus(milestone.status)
    new_status = data.status

    # Validate forward-only transition
    allowed_next = _VALID_STATUS_TRANSITIONS.get(current_status, [])
    if new_status not in allowed_next:
        if not allowed_next:
            raise ValidationException(
                f"Milestone is already in terminal state: '{current_status.value}'. "
                "Completed milestones cannot be changed."
            )
        raise ValidationException(
            f"Invalid status transition: '{current_status.value}' → '{new_status.value}'. "
            f"Allowed next: {[s.value for s in allowed_next]}"
        )

    old_status = milestone.status
    milestone.status = new_status.value

    # Append remarks if provided
    if data.remarks:
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        note = f"[{timestamp}] {data.remarks}"
        milestone.remarks = (
            f"{milestone.remarks}\n{note}" if milestone.remarks else note
        )

    # On COMPLETED — stamp who completed it and when
    if new_status == MilestoneStatus.COMPLETED:
        milestone.completed_by = current_user.id
        milestone.completed_at = datetime.now(UTC)

        # ── Notification hook ──────────────────────────────────────────────
        try:
            from app.services.notification_service import send_milestone_alert
            from app.schemas.milestone import STAGE_LABELS
            stage_enum = MilestoneStage(milestone.stage_name)
            stage_label = STAGE_LABELS.get(stage_enum, milestone.stage_name)
            send_milestone_alert(
                order_id=milestone.order_id,
                milestone_stage=milestone.stage_name,
                stage_label=stage_label,
                completed_at=milestone.completed_at,
                db=db,
            )
        except Exception as _notif_exc:
            # Notification failure must NEVER break the milestone update
            logger.warning(
                "Notification dispatch failed for milestone_id=%s: %s",
                milestone.id, _notif_exc,
            )

    _log_audit(
        db=db,
        user_id=current_user.id,
        action_type="UPDATE",
        target_id=milestone.id,
        order_id=milestone.order_id,
        description=(
            f"Milestone '{milestone.stage_name}' status: "
            f"{old_status} → {new_status.value}"
            + (f" | Remarks: {data.remarks}" if data.remarks else "")
        ),
    )

    db.commit()
    db.refresh(milestone)
    logger.info(
        "Milestone updated: milestone_id=%s %s→%s by user_id=%s",
        milestone.id, old_status, new_status.value, current_user.id,
    )
    return _to_response(milestone)


# ── Get order timeline ────────────────────────────────────────────────────────

def get_order_timeline(
    order_id: int,
    current_user: User,
    db: Session,
) -> OrderTimelineResponse:
    """
    Build the full chronological timeline for an order, merging milestone steps
    and event logs (e.g. document approvals/rejections/uploads) into one view.
    """
    order = _get_order_or_404(order_id, db)

    milestones = (
        db.query(Milestone)
        .options(joinedload(Milestone.completer))
        .filter(Milestone.order_id == order_id)
        .all()
    )

    # Sort milestones by sequence first to compute standard progress stats
    stage_order_map = {stage.value: i for i, stage in enumerate(STAGE_SEQUENCE)}
    milestones.sort(key=lambda m: stage_order_map.get(m.stage_name, 99))

    milestone_items = [_to_timeline_item(m) for m in milestones]

    # Compute progress stats
    total = len(milestone_items)
    completed = sum(1 for m in milestone_items if m.is_completed)
    overall_progress = round((completed / total * 100), 1) if total > 0 else 0.0

    active_stage: Optional[MilestoneStage] = None
    for item in milestone_items:
        if item.is_active:
            active_stage = MilestoneStage(item.stage_name) if item.stage_name in {s.value for s in STAGE_SEQUENCE} else None
            break

    # Fetch OrderEvents
    from app.models.order_event import OrderEvent
    events = db.query(OrderEvent).filter(OrderEvent.order_id == order_id).all()
    
    event_items = []
    for e in events:
        event_items.append(
            MilestoneTimelineItem(
                id=e.id,
                order_id=e.order_id,
                stage_name=e.event_type,
                stage_label=e.event_type.replace("_", " ").title(),
                stage_index=None,
                status=None,
                is_active=False,
                is_completed=True,
                remarks=e.description,
                completed_at=e.created_at,
                created_at=e.created_at,
                completer=None,
                item_type="event"
            )
        )

    # Merge milestones and events, then sort chronologically
    merged_items = milestone_items + event_items
    merged_items.sort(key=lambda x: x.completed_at or x.created_at)

    return OrderTimelineResponse(
        order_id=order.id,
        order_code=order.order_code,
        total_stages=total,
        completed_stages=completed,
        overall_progress=overall_progress,
        active_stage=active_stage,
        milestones=merged_items,
    )

