"""
app/schemas/milestone.py

Pydantic schemas for the Milestone tracking module.

9-stage milestone sequence (from SQL ENUM):
  1. PROCUREMENT
  2. RAW_MATERIAL_VERIFIED
  3. QA_TESTING
  4. PACKAGING_STARTED
  5. PACKAGING_COMPLETED
  6. DOCUMENTS_UPLOADED
  7. CONTAINER_LOADING
  8. SHIPMENT_DISPATCHED
  9. DELIVERED

Status per milestone:
  PENDING → IN_PROGRESS → COMPLETED
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ── Enums (match SQL exactly) ─────────────────────────────────────────────────

class MilestoneStage(str, Enum):
    PROCUREMENT           = "PROCUREMENT"
    RAW_MATERIAL_VERIFIED = "RAW_MATERIAL_VERIFIED"
    QA_TESTING            = "QA_TESTING"
    PACKAGING_STARTED     = "PACKAGING_STARTED"
    PACKAGING_COMPLETED   = "PACKAGING_COMPLETED"
    DOCUMENTS_UPLOADED    = "DOCUMENTS_UPLOADED"
    CONTAINER_LOADING     = "CONTAINER_LOADING"
    SHIPMENT_DISPATCHED   = "SHIPMENT_DISPATCHED"
    DELIVERED             = "DELIVERED"


class MilestoneStatus(str, Enum):
    PENDING     = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED   = "COMPLETED"


# ── Ordered sequence (used for validation + timeline rendering) ───────────────

STAGE_SEQUENCE: List[MilestoneStage] = [
    MilestoneStage.PROCUREMENT,
    MilestoneStage.RAW_MATERIAL_VERIFIED,
    MilestoneStage.QA_TESTING,
    MilestoneStage.PACKAGING_STARTED,
    MilestoneStage.PACKAGING_COMPLETED,
    MilestoneStage.DOCUMENTS_UPLOADED,
    MilestoneStage.CONTAINER_LOADING,
    MilestoneStage.SHIPMENT_DISPATCHED,
    MilestoneStage.DELIVERED,
]

# Human-readable labels for frontend timeline rendering
STAGE_LABELS: dict[MilestoneStage, str] = {
    MilestoneStage.PROCUREMENT:           "Procurement",
    MilestoneStage.RAW_MATERIAL_VERIFIED: "Raw Material Verified",
    MilestoneStage.QA_TESTING:            "QA Testing",
    MilestoneStage.PACKAGING_STARTED:     "Packaging Started",
    MilestoneStage.PACKAGING_COMPLETED:   "Packaging Completed",
    MilestoneStage.DOCUMENTS_UPLOADED:    "Documents Uploaded",
    MilestoneStage.CONTAINER_LOADING:     "Container Loading",
    MilestoneStage.SHIPMENT_DISPATCHED:   "Shipment Dispatched",
    MilestoneStage.DELIVERED:             "Delivered",
}


# ── Request schemas ───────────────────────────────────────────────────────────

class MilestoneCreate(BaseModel):
    """
    Body for POST /api/v1/orders/{order_id}/milestones

    Creates a single milestone for an order.
    Stage must not already exist for the same order.
    """
    stage_name: MilestoneStage
    remarks: Optional[str] = Field(None, max_length=2000)

    model_config = {
        "json_schema_extra": {
            "example": {
                "stage_name": "PROCUREMENT",
                "remarks": "500 MT Turmeric sourced from Erode market."
            }
        }
    }


class MilestoneStatusUpdate(BaseModel):
    """
    Body for PATCH /api/v1/milestones/{milestone_id}

    Updates the status of an existing milestone.
    Transitions: PENDING → IN_PROGRESS → COMPLETED
    Completing a milestone triggers a customer notification.
    """
    status: MilestoneStatus = Field(
        ..., description="New status. Must follow PENDING → IN_PROGRESS → COMPLETED"
    )
    remarks: Optional[str] = Field(
        None, max_length=2000,
        description="Optional remarks to append on this status update"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "COMPLETED",
                "remarks": "QA passed. Moisture: 8.2%, Purity: 98.5%."
            }
        }
    }


class MilestoneBulkCreate(BaseModel):
    """
    Body for POST /api/v1/orders/{order_id}/milestones/bulk

    Initialize all 9 milestones for an order in one call.
    All stages created with status = PENDING.
    """
    pass  # No body needed — stages are auto-derived from STAGE_SEQUENCE


# ── Response schemas ──────────────────────────────────────────────────────────

class CompleterInfo(BaseModel):
    """Embedded user info for who completed the milestone."""
    id: int
    full_name: str
    role: str

    model_config = {"from_attributes": True}


class MilestoneResponse(BaseModel):
    """Single milestone — returned by create and update endpoints."""
    id: int
    order_id: int
    stage_name: MilestoneStage
    stage_label: str            # human-readable label added by service
    status: MilestoneStatus
    remarks: Optional[str]
    completed_by: Optional[int]
    completed_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class MilestoneTimelineItem(BaseModel):
    """
    A single node in the order timeline response.
    Can represent either a milestone progress step or an order event log.
    """
    id: int
    order_id: int
    stage_name: str
    stage_label: str
    stage_index: Optional[int] = None
    status: Optional[str] = None
    is_active: bool = False
    is_completed: bool = False
    remarks: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    completer: Optional[CompleterInfo] = None
    item_type: str = "milestone"  # "milestone" or "event"

    model_config = {"from_attributes": True}



class OrderTimelineResponse(BaseModel):
    """
    Full timeline for an order — returned by GET /orders/{id}/timeline

    Contains all milestone nodes in sequence order.
    active_stage is the current IN_PROGRESS stage (or None if not started).
    overall_progress is the percentage of COMPLETED milestones (0–100).
    """
    order_id: int
    order_code: str
    total_stages: int
    completed_stages: int
    overall_progress: float     # 0.0 – 100.0
    active_stage: Optional[MilestoneStage]
    milestones: List[MilestoneTimelineItem]
