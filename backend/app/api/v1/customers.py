import logging
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import DbSession, StaffUser, AdminUser
from app.core.exceptions import ConflictException
from app.models.customer import Customer
from app.schemas.common import SuccessResponse
from app.schemas.customer import CustomerResponse, CustomerOnboard, CustomerListResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get(
    "",
    response_model=CustomerListResponse,
    summary="List all customers",
    description="Returns a list of all export customers/buyers. Accessible to staff users only.",
)
def list_customers(
    current_user: StaffUser,
    db: DbSession,
) -> CustomerListResponse:
    customers = db.query(Customer).order_by(Customer.company_name.asc()).all()
    # Pydantic is configured with from_attributes = True, so it will parse the DB models automatically
    return CustomerListResponse(data=[CustomerResponse.model_validate(c) for c in customers])


@router.post(
    "",
    response_model=SuccessResponse[CustomerResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new customer profile",
    description="Registers a new buyer company in the system. Requires ADMIN or SUPER_ADMIN role.",
)
def create_customer(
    body: CustomerOnboard,
    current_user: AdminUser,
    db: DbSession,
) -> SuccessResponse[CustomerResponse]:
    # Check for duplicates by email or company name
    email_clean = body.email.strip().lower()
    company_clean = body.company_name.strip()

    existing_name = db.query(Customer).filter(Customer.company_name == company_clean).first()
    if existing_name:
        raise ConflictException(f"A customer with company name '{company_clean}' already exists")

    existing_email = db.query(Customer).filter(Customer.email == email_clean).first()
    if existing_email:
        raise ConflictException(f"A customer with email '{email_clean}' already exists")

    customer = Customer(
        company_name=company_clean,
        contact_person=body.contact_person,
        email=email_clean,
        phone=body.phone.strip(),
        country=body.country,
        address=body.address,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)

    # Trigger custom audit logging
    from app.services.order_service import _log_audit
    _log_audit(
        db=db,
        user_id=current_user.id,
        action_type="CREATE",
        target_id=customer.id,
        description=f"Customer profile '{customer.company_name}' created.",
    )
    db.commit()

    return SuccessResponse(
        data=CustomerResponse.model_validate(customer),
        message=f"Customer '{customer.company_name}' created successfully",
    )
