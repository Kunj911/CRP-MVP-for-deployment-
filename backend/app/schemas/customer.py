import re
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator

class CustomerResponse(BaseModel):
    id: int
    company_name: str
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None
    address: Optional[str] = None
    storage_quota_mb: int
    created_at: datetime

    class Config:
        from_attributes = True

class CustomerOnboard(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=200, description="Name of the buyer company")
    contact_person: Optional[str] = Field(None, max_length=100, description="Full name of contact person")
    email: EmailStr = Field(..., description="Email address for user account creation")
    phone: str = Field(..., min_length=5, max_length=20, description="Phone number for validation")
    country: Optional[str] = Field(None, max_length=100, description="Country of destination / location")
    address: Optional[str] = Field(None, description="Physical address")
    notes: Optional[str] = Field(None, description="Optional onboarding notes")
    password: Optional[str] = Field(
        None, min_length=8,
        description="Custom password for the new customer login. Leave blank for default Welcome@1234"
    )

    @field_validator("company_name")
    @classmethod
    def strip_company_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Company name cannot be blank")
        return trimmed

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Phone number cannot be blank")
        if not re.match(r"^\+?[\d\s\-()]+$", trimmed):
            raise ValueError("Phone number must contain only digits, spaces, dashes, parentheses, or '+'")
        return trimmed

class ActiveOrderSummary(BaseModel):
    id: int
    order_code: str
    product_name: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    shipment_status: str


class ActiveCustomerResponse(BaseModel):
    id: int
    company_name: str
    contact_person: Optional[str] = None
    email: Optional[str] = None
    login_email: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    address: Optional[str] = None
    active_orders_count: int = 0
    active_orders: List[ActiveOrderSummary] = []

    class Config:
        from_attributes = True


class CustomerListResponse(BaseModel):
    status: str = "success"
    data: List[CustomerResponse]
