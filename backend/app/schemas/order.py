"""
app/schemas/order.py

Pydantic request and response schemas for the Order module.

Shipment status lifecycle (from SQL ENUM):
  CREATED → PROCUREMENT → QA_TESTING → PACKAGING →
  DOCUMENTATION → READY_FOR_SHIPMENT → SHIPPED → DELIVERED

Schema naming convention:
  OrderCreate        — POST /orders body
  OrderUpdate        — PATCH /orders/{id} body (all fields optional)
  OrderStatusUpdate  — PATCH /orders/{id}/status (status only)
  OrderResponse      — single order returned to client
  OrderListItem      — lightweight item used in paginated list
  OrderDetailResponse— full order with nested customer info
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator
from app.schemas.customer import CustomerOnboard


# ── Shipment status enum ──────────────────────────────────────────────────────

class ShipmentStatus(str, Enum):
    CREATED             = "CREATED"
    PROCUREMENT         = "PROCUREMENT"
    QA_TESTING          = "QA_TESTING"
    PACKAGING           = "PACKAGING"
    DOCUMENTATION       = "DOCUMENTATION"
    READY_FOR_SHIPMENT  = "READY_FOR_SHIPMENT"
    SHIPPED             = "SHIPPED"
    DELIVERED           = "DELIVERED"
    CANCELLED           = "CANCELLED"


# ── Status transition rules ───────────────────────────────────────────────────
# Enforced in service layer — only forward transitions allowed.

VALID_TRANSITIONS: dict[ShipmentStatus, list[ShipmentStatus]] = {
    ShipmentStatus.CREATED:            [ShipmentStatus.PROCUREMENT, ShipmentStatus.CANCELLED],
    ShipmentStatus.PROCUREMENT:        [ShipmentStatus.QA_TESTING, ShipmentStatus.CANCELLED],
    ShipmentStatus.QA_TESTING:         [ShipmentStatus.PACKAGING, ShipmentStatus.CANCELLED],
    ShipmentStatus.PACKAGING:          [ShipmentStatus.DOCUMENTATION, ShipmentStatus.CANCELLED],
    ShipmentStatus.DOCUMENTATION:      [ShipmentStatus.READY_FOR_SHIPMENT, ShipmentStatus.CANCELLED],
    ShipmentStatus.READY_FOR_SHIPMENT: [ShipmentStatus.SHIPPED, ShipmentStatus.CANCELLED],
    ShipmentStatus.SHIPPED:            [ShipmentStatus.DELIVERED],
    ShipmentStatus.DELIVERED:          [],   # terminal state
    ShipmentStatus.CANCELLED:          [],   # terminal state — cannot revert
}


# ── Request schemas ───────────────────────────────────────────────────────────

class OrderCreate(BaseModel):
    """Body for POST /api/v1/orders"""

    customer_id: int = Field(..., gt=0, description="ID of the customer (buyer)")
    product_name: str = Field(..., min_length=1, max_length=200)
    quantity: Optional[Decimal] = Field(
        None, gt=0, decimal_places=2, description="Quantity (e.g. 500.00)"
    )
    unit: Optional[str] = Field(
        None, max_length=20, description="Unit of measure: kg, MT, bags, etc."
    )
    expected_dispatch_date: Optional[date] = None
    expected_delivery_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=2000)

    @field_validator("product_name")
    @classmethod
    def strip_product_name(cls, v: str) -> str:
        return v.strip()

    @model_validator(mode="after")
    def validate_dates(self) -> "OrderCreate":
        if (
            self.expected_dispatch_date
            and self.expected_delivery_date
            and self.expected_delivery_date < self.expected_dispatch_date
        ):
            raise ValueError(
                "expected_delivery_date cannot be before expected_dispatch_date"
            )
        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "customer_id": 1,
                "product_name": "Turmeric Finger Grade A",
                "quantity": 500.00,
                "unit": "MT",
                "expected_dispatch_date": "2026-06-10",
                "expected_delivery_date": "2026-07-05",
                "notes": "Handle with care — humidity-sensitive cargo.",
            }
        }
    }


class OrderUpdate(BaseModel):
    """
    Body for PATCH /api/v1/orders/{order_id}
    All fields optional — only provided fields will be updated.
    Status changes must go through OrderStatusUpdate instead.
    """
    product_name: Optional[str] = Field(None, min_length=1, max_length=200)
    quantity: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    unit: Optional[str] = Field(None, max_length=20)
    expected_dispatch_date: Optional[date] = None
    expected_delivery_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=2000)

    @model_validator(mode="after")
    def at_least_one_field(self) -> "OrderUpdate":
        if all(v is None for v in self.model_dump().values()):
            raise ValueError("At least one field must be provided for update")
        return self


class OrderStatusUpdate(BaseModel):
    """Body for PATCH /api/v1/orders/{order_id}/status"""
    status: ShipmentStatus = Field(
        ..., description="New shipment status — must be a valid forward transition"
    )
    notes: Optional[str] = Field(
        None, max_length=500, description="Optional note for this status change"
    )


# ── Nested response schemas ───────────────────────────────────────────────────

class CustomerSummary(BaseModel):
    """Embedded customer info inside OrderDetailResponse."""
    id: int
    company_name: str
    contact_person: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    country: Optional[str]

    model_config = {"from_attributes": True}


class CreatorSummary(BaseModel):
    """Embedded creator (User) info inside OrderDetailResponse."""
    id: int
    full_name: str
    role: str

    model_config = {"from_attributes": True}


# ── Response schemas ──────────────────────────────────────────────────────────

class OrderListItem(BaseModel):
    """
    Lightweight order representation — used in paginated list responses.
    Avoids loading all relationships.
    """
    id: int
    order_code: str
    customer_id: int
    company_name: str          # denormalized from customer join
    destination_country: Optional[str] = None  # denormalized from customer join
    product_name: str
    quantity: Optional[Decimal]
    unit: Optional[str]
    shipment_status: ShipmentStatus
    expected_dispatch_date: Optional[date]
    expected_delivery_date: Optional[date]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    """
    Full single-order response — returned by create, get-by-id, update.
    """
    id: int
    order_code: str
    customer_id: int
    product_name: str
    quantity: Optional[Decimal]
    unit: Optional[str]
    shipment_status: ShipmentStatus
    expected_dispatch_date: Optional[date]
    expected_delivery_date: Optional[date]
    notes: Optional[str]
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderDetailResponse(OrderResponse):
    """
    Extended order response with nested customer and creator details.
    Returned by GET /api/v1/orders/{order_id}.
    """
    customer: Optional[CustomerSummary] = None
    creator: Optional[CreatorSummary] = None


# ── Filter / query params ─────────────────────────────────────────────────────

class OrderFilters(BaseModel):
    """
    Query parameters for GET /api/v1/orders list endpoint.
    All filters are optional and combined with AND logic.
    """
    customer_id: Optional[int] = Field(None, gt=0)
    status: Optional[ShipmentStatus] = None
    product_name: Optional[str] = Field(None, max_length=200)
    from_date: Optional[date] = Field(None, description="Filter orders created on or after this date")
    to_date: Optional[date] = Field(None, description="Filter orders created on or before this date")
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class OrderCreateFields(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=200)
    quantity: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    unit: Optional[str] = Field(None, max_length=20)
    expected_dispatch_date: Optional[date] = None
    expected_delivery_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=2000)

    @field_validator("product_name")
    @classmethod
    def strip_product_name(cls, v: str) -> str:
        return v.strip()

    @model_validator(mode="after")
    def validate_dates(self) -> "OrderCreateFields":
        if (
            self.expected_dispatch_date
            and self.expected_delivery_date
            and self.expected_delivery_date < self.expected_dispatch_date
        ):
            raise ValueError(
                "expected_delivery_date cannot be before expected_dispatch_date"
            )
        return self


class OrderWithNewCustomerCreate(BaseModel):
    customer: CustomerOnboard
    order: OrderCreateFields
