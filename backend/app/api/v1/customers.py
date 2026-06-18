import logging
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import DbSession, StaffUser, AdminUser, SuperAdminUser
from app.core.exceptions import ConflictException, NotFoundException
from app.models.customer import Customer
from app.models.order import Order
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.customer import (
    CustomerResponse,
    CustomerOnboard,
    CustomerListResponse,
    ActiveCustomerResponse,
)

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
    description="Registers a new buyer company in the system. Requires SUPER_ADMIN role.",
)
def create_customer(
    body: CustomerOnboard,
    current_user: SuperAdminUser,
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


@router.get(
    "/active",
    summary="List all customers with their active orders",
    description="Returns all customers with their active (non-delivered, non-cancelled) orders. Accessible to staff users only.",
)
def list_active_customers(
    current_user: StaffUser,
    db: DbSession,
) -> List[ActiveCustomerResponse]:
    customers = (
        db.query(Customer)
        .options(joinedload(Customer.orders), joinedload(Customer.users))
        .order_by(Customer.company_name.asc())
        .all()
    )

    result = []
    for c in customers:
        active_orders = [
            o
            for o in c.orders
            if o.shipment_status not in ("DELIVERED", "CANCELLED")
        ]

        login_email = None
        for u in c.users:
            if u.role == "CUSTOMER":
                login_email = u.email
                break

        summary_orders = []
        for o in active_orders:
            try:
                summary_orders.append(ActiveOrderSummary(
                    id=o.id,
                    order_code=o.order_code,
                    product_name=o.product_name,
                    quantity=float(o.quantity) if o.quantity is not None else None,
                    unit=o.unit,
                    shipment_status=o.shipment_status,
                ))
            except Exception as e:
                logger.error("Failed to build ActiveOrderSummary for order %s: %s", o.id, e)
                raise

        result.append(ActiveCustomerResponse(
            id=c.id,
            company_name=c.company_name,
            contact_person=c.contact_person,
            email=c.email,
            login_email=login_email,
            phone=c.phone,
            country=c.country,
            address=c.address,
            active_orders_count=len(summary_orders),
            active_orders=summary_orders,
        ))

    return result


@router.get(
    "/{customer_id}",
    response_model=SuccessResponse[CustomerResponse],
    summary="Get customer by ID",
    description="Returns a single customer profile by ID. Accessible to staff users only.",
)
def get_customer(
    customer_id: int,
    current_user: StaffUser,
    db: DbSession,
) -> SuccessResponse[CustomerResponse]:
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise NotFoundException("Customer", customer_id)
    return SuccessResponse(data=CustomerResponse.model_validate(customer))
