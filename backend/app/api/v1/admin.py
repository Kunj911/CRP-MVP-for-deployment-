import logging
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, SuperAdminUser
from app.config.settings import get_settings
from app.core.security import hash_password
from app.models.customer import Customer
from app.models.user import User
from app.models.order import Order
from app.models.milestone import Milestone
from app.models.order_event import OrderEvent
from app.models.document import Document
from app.models.order_document_requirement import OrderDocumentRequirement
from app.models.media_file import MediaFile
from app.models.notification import Notification
from app.models.audit_log import AuditLog
from sqlalchemy import text
from app.schemas.common import SuccessResponse

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["Admin"])


def _verify_seed_key(x_seed_key: str = Header(..., alias="x-seed-key")):
    if not settings.SEED_API_KEY:
        raise HTTPException(status_code=404, detail="Seed endpoint is not enabled")
    if x_seed_key != settings.SEED_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid seed key")


STAGES = [
    ("PROCUREMENT", "Raw materials sourced and verified from select growers."),
    ("RAW_MATERIAL_VERIFIED", "Raw material physical verification complete."),
    ("QA_TESTING", "Lab analysis cleared. Sample meets physical and chemical grades."),
    ("PACKAGING_STARTED", "Packaging process initiated."),
    ("PACKAGING_COMPLETED", "Bags packaged, vacuum sealed, and palletized."),
    ("DOCUMENTS_UPLOADED", "Export invoice, packing lists, and certificates prepared."),
    ("CONTAINER_LOADING", "Loaded into container and verified cargo seals."),
    ("SHIPMENT_DISPATCHED", "Dispatched via cargo transit."),
    ("DELIVERED", "Delivered to port destination warehouse."),
]

STATUS_RANK = {
    "CREATED": -1, "PROCUREMENT": 0, "QA_TESTING": 2, "PACKAGING": 4,
    "DOCUMENTATION": 5, "READY_FOR_SHIPMENT": 6, "SHIPPED": 7, "DELIVERED": 9,
    "CANCELLED": 10,
}

DOC_REQUIREMENTS = {
    "invoice": True, "purchase_order": True, "packing_list": True,
    "certificate_of_analysis": True, "product_specification": True,
    "bill_of_lading": False, "lab_report": False, "phytosanitary_certificate": False,
    "insurance_certificate": False, "certificate_of_origin": False, "other": False,
}


@router.post(
    "/seed",
    response_model=SuccessResponse[str],
    summary="Seed full demo dataset",
)
def seed_demo_database(
    _: None = Depends(_verify_seed_key),
    db: Session = Depends(get_db),
) -> SuccessResponse[str]:
    existing = db.query(Customer).first()
    if existing:
        raise HTTPException(status_code=409, detail="Database already contains data. Seed can only run on an empty database.")

    now = datetime.now()

    customers_data = [
        ("McCormick & Company", "Kunj", "kunj.fittree@gmail.com", "8866816365", "USA", "America/New_York",
         "24 Schilling Road, Hunt Valley, Maryland 21031, USA", 2000),
        ("Olam Food Ingredients", "Roomi", "roominesh.fittree@gmail.com", "9081751379", "Singapore", "Asia/Singapore",
         "7 Straits View, Marina One East Tower, Singapore 018936", 1500),
        ("Kerry Spice Group", "Yash", "yash.fittree@gmail.com", "9313049422", "Ireland", "Europe/Dublin",
         "Tralee Road, Co. Kerry, Ireland", 1500),
        ("Pacific Spice Company Inc", "Vaidhehi", "vaidehifittree@gmail.com", "+918160777033", "USA", "America/Los_Angeles",
         "6430 E. Slauson Ave, Commerce, CA 90040, USA", 2500),
    ]

    internal_users = [
        ("Poonam", "poonam.fittree@gmail.com", "WAREHOUSE", "Warehouse@1234", "+91-7426866027"),
        ("Poonam QA", "poonam.qa.fittree@gmail.com", "QA", "QA@1234", "+91-7426866027"),
        ("Poonam Docs", "poonam.docs.fittree@gmail.com", "DOCUMENTATION", "Document@1234", "+91-7426866027"),
        ("Kunj Mistry", "kunjalpesh@gmail.com", "SUPER_ADMIN", "Iamtheadmin@1234", "+91-8866816365"),
    ]

    customer_user_map = [
        ("Kunj McCormick", "kunj.fittree@gmail.com", "Kunj@1234", "8866816365", "McCormick & Company"),
        ("Roomi Olam", "roominesh.fittree@gmail.com", "Roomi@1234", "9081751379", "Olam Food Ingredients"),
        ("Yash Kerry", "yash.fittree@gmail.com", "Yash@1234", "9313049422", "Kerry Spice Group"),
        ("Vaidhehi Pacific", "vaidehifittree@gmail.com", "Vaidhehi@1234", "+918160777033", "Pacific Spice Company Inc"),
    ]

    orders_data = [
        ("ORD-2026-MC01", "McCormick & Company", "Turmeric Powder", 15000.00, "KG", "DELIVERED", "2026-05-10", "2026-05-25"),
        ("ORD-2026-MC02", "McCormick & Company", "Black Pepper", 12000.00, "KG", "SHIPPED", "2026-05-20", "2026-06-05"),
        ("ORD-2026-MC03", "McCormick & Company", "Red Chilli Powder", 8000.00, "KG", "DOCUMENTATION", "2026-06-01", "2026-06-15"),
        ("ORD-2026-MC04", "McCormick & Company", "Garlic Powder", 5000.00, "KG", "QA_TESTING", "2026-06-05", "2026-06-20"),
        ("ORD-2026-MC05", "McCormick & Company", "Amchur Powder", 3000.00, "KG", "CREATED", "2026-06-12", "2026-06-28"),
        ("ORD-2026-OF01", "Olam Food Ingredients", "Cumin Powder", 20000.00, "KG", "DELIVERED", "2026-05-08", "2026-05-24"),
        ("ORD-2026-OF02", "Olam Food Ingredients", "Coriander Powder", 18000.00, "KG", "READY_FOR_SHIPMENT", "2026-05-28", "2026-06-12"),
        ("ORD-2026-OF03", "Olam Food Ingredients", "Ginger Powder", 10000.00, "KG", "PACKAGING", "2026-06-03", "2026-06-18"),
        ("ORD-2026-OF04", "Olam Food Ingredients", "White Pepper", 6000.00, "KG", "PROCUREMENT", "2026-06-10", "2026-06-25"),
        ("ORD-2026-KS01", "Kerry Spice Group", "Cinnamon Powder", 9000.00, "KG", "DELIVERED", "2026-05-12", "2026-05-27"),
        ("ORD-2026-KS02", "Kerry Spice Group", "Cardamom Powder", 4000.00, "KG", "SHIPPED", "2026-05-22", "2026-06-06"),
        ("ORD-2026-KS03", "Kerry Spice Group", "Onion Powder", 7500.00, "KG", "QA_TESTING", "2026-06-04", "2026-06-19"),
        ("ORD-2026-KS04", "Kerry Spice Group", "Amchur Powder", 5000.00, "KG", "PROCUREMENT", "2026-06-09", "2026-06-24"),
        ("ORD-2026-PS01", "Pacific Spice Company Inc", "Red Chilli Powder", 22000.00, "KG", "DELIVERED", "2026-05-09", "2026-05-24"),
        ("ORD-2026-PS02", "Pacific Spice Company Inc", "Turmeric Powder", 14000.00, "KG", "SHIPPED", "2026-05-21", "2026-06-05"),
        ("ORD-2026-PS03", "Pacific Spice Company Inc", "Black Pepper", 11000.00, "KG", "PACKAGING", "2026-06-02", "2026-06-17"),
        ("ORD-2026-PS04", "Pacific Spice Company Inc", "Cumin Powder", 3500.00, "KG", "CREATED", "2026-06-11", "2026-06-26"),
        ("ORD-2026-PS05", "Pacific Spice Company Inc", "Garlic Powder", 9000.00, "KG", "DOCUMENTATION", "2026-05-31", "2026-06-15"),
    ]

    # Seed Customers
    customer_by_name = {}
    for name, contact, email, phone, country, tz, addr, quota in customers_data:
        c = Customer(company_name=name, contact_person=contact, email=email, phone=phone,
                     country=country, timezone=tz, address=addr, storage_quota_mb=quota)
        db.add(c)
        db.flush()
        customer_by_name[name] = c

    # Seed Internal Users
    staff_by_role = {}
    for name, email, role, pwd, phone in internal_users:
        u = User(full_name=name, email=email, role=role,
                 password_hash=hash_password(pwd), phone=phone,
                 is_active=True, mfa_enabled=False)
        db.add(u)
        db.flush()
        staff_by_role[role] = u
    admin_user = staff_by_role["SUPER_ADMIN"]

    # Seed Customer Users
    customer_user_by_email = {}
    for name, email, pwd, phone, company in customer_user_map:
        u = User(full_name=name, email=email, role="CUSTOMER",
                 password_hash=hash_password(pwd), phone=phone,
                 customer_id=customer_by_name[company].id,
                 is_active=True, mfa_enabled=False)
        db.add(u)
        db.flush()
        customer_user_by_email[email] = u

    db.flush()

    # Seed Orders
    order_records = []
    for code, company, product, qty, unit, status, dispatch, delivery in orders_data:
        o = Order(order_code=code, customer_id=customer_by_name[company].id,
                  product_name=product, quantity=qty, unit=unit,
                  shipment_status=status,
                  expected_dispatch_date=date.fromisoformat(dispatch),
                  expected_delivery_date=date.fromisoformat(delivery),
                  notes=f"Payment status: Paid | Premium grade ground {product.lower()} shipment bound for {customer_by_name[company].country}.",
                  created_by=admin_user.id)
        db.add(o)
        db.flush()
        order_records.append(o)

    db.flush()

    customer_by_id = {c.id: c for c in customer_by_name.values()}

    # Seed dependent data per order
    for o in order_records:
        status_index = STATUS_RANK.get(o.shipment_status, -1)
        customer = customer_by_id[o.customer_id]

        # Order Event
        db.add(OrderEvent(order_id=o.id, event_type="status_changed",
                          description="Order created and initial milestone set.",
                          created_at=now - timedelta(days=15)))

        # Milestones
        milestone_ids = {}
        for idx, (stage_name, desc) in enumerate(STAGES):
            m = Milestone(order_id=o.id, stage_name=stage_name, remarks=desc)
            if idx < status_index:
                m.status = "COMPLETED"
                m.completed_at = now - timedelta(days=(status_index - idx) * 2)
                role_user = staff_by_role.get(_stage_role(stage_name))
                m.completed_by = role_user.id if role_user else None
            elif idx == status_index:
                m.status = "IN_PROGRESS"
            else:
                m.status = "PENDING"
            db.add(m)
            db.flush()
            milestone_ids[stage_name] = m.id

        # Documents
        seeded_docs = {}
        doc_user = staff_by_role.get("DOCUMENTATION")
        qa_user = staff_by_role.get("QA")
        cust_user = customer_user_by_email.get(customer.email)

        doc_defs = [
            ("INVOICE", "commercial_invoice_%s.pdf", doc_user, -8),
            ("product_specification", "product_specification_%s.pdf", doc_user, -8),
            ("purchase_order", "purchase_order_%s.pdf", cust_user, -9),
        ]
        if status_index >= 2:
            doc_defs += [
                ("LAB_REPORT", "laboratory_analysis_%s.pdf", qa_user, -6),
                ("certificate_of_analysis", "coa_%s.pdf", qa_user, -6),
            ]
        if status_index >= 3:
            doc_defs += [("PACKING_LIST", "packing_list_%s.pdf", doc_user, -4)]
        if status_index >= 4:
            doc_defs += [("PHYTOSANITARY_CERTIFICATE", "phytosanitary_certificate_%s.pdf", doc_user, -2)]
        if status_index >= 6:
            doc_defs += [("bill_of_lading", "bill_of_lading_%s.pdf", doc_user, -1)]

        for dtype, fname_tpl, uploader, day_offset in doc_defs:
            fname = fname_tpl % o.order_code
            doc = Document(order_id=o.id, document_type=dtype, file_name=fname,
                           file_url=f"/uploads/{o.order_code}/documents/{fname}",
                           file_size=102400 if dtype == "invoice" else 85000,
                           uploaded_by=uploader.id if uploader else admin_user.id,
                           status="approved", visibility="customer_visible",
                           reviewed_by=admin_user.id,
                           reviewed_at=now + timedelta(days=day_offset))
            db.add(doc)
            db.flush()
            seeded_docs[dtype] = doc.id

        # Document checklist
        for dtype, req in DOC_REQUIREMENTS.items():
            uploaded = dtype in seeded_docs
            db.add(OrderDocumentRequirement(
                order_id=o.id, document_type=dtype, required=req,
                uploaded=uploaded, approved=uploaded,
                uploaded_at=now - timedelta(days=8) if uploaded else None,
                approved_at=now - timedelta(days=7) if uploaded else None,
                approved_by=admin_user.id if uploaded else None,
                document_id=seeded_docs.get(dtype),
            ))

        # Media files
        if status_index >= 0:
            db.add(MediaFile(order_id=o.id, milestone_id=milestone_ids["PROCUREMENT"],
                             media_type="PROCUREMENT_IMAGE",
                             file_name=f"raw_material_{o.order_code}.jpg",
                             file_url=f"/uploads/{o.order_code}/media/raw_material_{o.order_code}.jpg",
                             file_size=245000,
                             uploaded_by=staff_by_role["WAREHOUSE"].id))
        if status_index >= 4:
            db.add(MediaFile(order_id=o.id, milestone_id=milestone_ids["PACKAGING_COMPLETED"],
                             media_type="PACKAGING_IMAGE",
                             file_name=f"packaging_{o.order_code}.jpg",
                             file_url=f"/uploads/{o.order_code}/media/packaging_{o.order_code}.jpg",
                             file_size=189000,
                             uploaded_by=staff_by_role["WAREHOUSE"].id))

        # Notifications
        if cust_user:
            db.add(Notification(order_id=o.id, user_id=cust_user.id,
                                title="Order Confirmed", notification_type="order",
                                message=f"Your export order {o.order_code} has been successfully registered.",
                                delivery_status="SENT", sent_at=now - timedelta(days=10),
                                is_read=True, related_order_id=o.id))
            if status_index >= 2 and "certificate_of_analysis" in seeded_docs:
                db.add(Notification(order_id=o.id, user_id=cust_user.id,
                                    title="Quality Verification Passed", notification_type="qa",
                                    message=f"QA analysis completed successfully for order {o.order_code}. High purity confirmed.",
                                    delivery_status="SENT", sent_at=now - timedelta(days=5),
                                    is_read=False, related_order_id=o.id,
                                    related_document_id=seeded_docs["certificate_of_analysis"]))
            if status_index >= 6:
                db.add(Notification(order_id=o.id, user_id=cust_user.id,
                                    title="Shipment Dispatched", notification_type="shipment",
                                    message=f"Shipment dispatched for order {o.order_code}. Vessel in transit.",
                                    delivery_status="SENT", sent_at=now - timedelta(days=2),
                                    is_read=False, related_order_id=o.id))

        # Audit log
        db.add(AuditLog(user_id=admin_user.id, action_type="create",
                        target_table="orders", target_id=o.id,
                        description=f"Admin created order {o.order_code}."))

    db.commit()

    counts = {}
    for table_name in ["customers", "users", "orders", "milestones", "order_events",
                        "documents", "order_document_requirements", "media_files",
                        "notifications", "audit_logs"]:
        counts[table_name] = db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()

    msg = "Seeded: " + ", ".join(f"{k}={v}" for k, v in counts.items())
    logger.info("Seed complete: %s", msg)
    return SuccessResponse(data=msg, message="Database seeded successfully")


class DeactivateUserRequest(BaseModel):
    user_id: int
    deactivate: bool = True


@router.post(
    "/users/deactivate",
    response_model=SuccessResponse[str],
    summary="Activate or deactivate a user account (SUPER_ADMIN only)",
)
def deactivate_user(
    body: DeactivateUserRequest,
    current_user: SuperAdminUser,
    db: Session = Depends(get_db),
) -> SuccessResponse[str]:
    user = db.query(User).filter(User.id == body.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Cannot deactivate another SUPER_ADMIN")

    user.is_active = body.deactivate
    action = "activated" if body.deactivate else "deactivated"
    db.add(AuditLog(
        user_id=current_user.id,
        action_type="UPDATE",
        target_table="users",
        target_id=user.id,
        description=f"User '{user.email}' {action} by {current_user.full_name}.",
    ))
    db.commit()
    logger.info("User %s %s: user_id=%s by %s", action, user.email, user.id, current_user.email)
    return SuccessResponse(
        data=f"User '{user.email}' {action} successfully",
        message=f"User account has been {action}.",
    )


@router.post(
    "/settings/test-email",
    response_model=SuccessResponse[str],
    summary="Send a test email to verify email configuration",
)
def send_test_email(
    current_user: SuperAdminUser,
) -> SuccessResponse[str]:
    """Send a test email to the current user's email address to verify the email engine is working."""
    from app.services.channels.email_channel import send_email

    try:
        success = send_email(
            to_address=current_user.email,
            subject="Test Email from Live-Trace",
            body_text=(
                f"Hello {current_user.full_name},\n\n"
                f"This is a test email from Live-Trace by Fittree International LLP.\n"
                f"If you received this, the email engine is working correctly.\n\n"
                f"Regards,\nLive-Trace Team"
            ),
            body_html=(
                f"<h2>Test Email</h2>"
                f"<p>Hello {current_user.full_name},</p>"
                f"<p>This is a test email from <strong>Live-Trace</strong> by Fittree International LLP.</p>"
                f"<p>If you received this, the email engine is working correctly.</p>"
                f"<hr><p style='color:#666;font-size:12px'>Live-Trace by Fittree International LLP</p>"
            ),
        )
        if success:
            logger.info("Test email sent successfully to %s", current_user.email)
            return SuccessResponse(
                data=f"Test email sent to {current_user.email}",
                message="Email sent successfully. Check your inbox.",
            )
        else:
            logger.error("Test email failed to send to %s", current_user.email)
            return SuccessResponse(
                data="Email delivery failed",
                message="Failed to send email. Check server logs for details.",
            )
    except Exception as e:
        logger.error("Test email exception for %s: %s", current_user.email, e)
        return SuccessResponse(
            data=str(e),
            message="An error occurred while sending the test email.",
        )


def _stage_role(stage_name: str) -> str | None:
    roles = {
        "PROCUREMENT": "WAREHOUSE",
        "RAW_MATERIAL_VERIFIED": "QA",
        "QA_TESTING": "QA",
        "PACKAGING_STARTED": "WAREHOUSE",
        "PACKAGING_COMPLETED": "WAREHOUSE",
        "DOCUMENTS_UPLOADED": "DOCUMENTATION",
        "CONTAINER_LOADING": "WAREHOUSE",
        "SHIPMENT_DISPATCHED": "SUPER_ADMIN",
        "DELIVERED": "SUPER_ADMIN",
    }
    return roles.get(stage_name)
