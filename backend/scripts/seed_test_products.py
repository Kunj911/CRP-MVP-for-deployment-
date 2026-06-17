"""
scripts/seed_test_products.py

Add sample multi-product orders to existing customers for testing.

Usage:
  cd backend
  python -m scripts.seed_test_products
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import SessionLocal
from app.models.customer import Customer
from app.models.order import Order
from app.models.order_product import OrderProduct
from app.models.user import User
from app.services.milestone_service import initialize_all_milestones
from app.schemas.order import ShipmentStatus
from datetime import date, timedelta


SAMPLE_ORDERS = [
    {
        "product_name": "Mixed Spices",
        "products": [
            {"product_name": "Turmeric Powder", "quantity": 500, "unit": "KG", "notes": "Premium Export Grade"},
            {"product_name": "Black Pepper", "quantity": 200, "unit": "KG", "notes": "Export Quality"},
            {"product_name": "Ginger Powder", "quantity": 100, "unit": "KG", "notes": ""},
        ],
        "status": "PROCUREMENT",
    },
    {
        "product_name": "Spice Blend",
        "products": [
            {"product_name": "Cardamom", "quantity": 80, "unit": "KG", "notes": "Green cardamom"},
            {"product_name": "Cumin Seeds", "quantity": 300, "unit": "KG", "notes": ""},
            {"product_name": "Coriander Seeds", "quantity": 400, "unit": "KG", "notes": ""},
        ],
        "status": "QA_TESTING",
    },
    {
        "product_name": "Premium Exports Mix",
        "products": [
            {"product_name": "Cloves", "quantity": 50, "unit": "KG", "notes": "Hand-picked"},
            {"product_name": "Cinnamon Sticks", "quantity": 120, "unit": "KG", "notes": "Grade A"},
            {"product_name": "Nutmeg", "quantity": 60, "unit": "KG", "notes": ""},
            {"product_name": "Star Anise", "quantity": 40, "unit": "KG", "notes": ""},
            {"product_name": "Fennel Seeds", "quantity": 200, "unit": "KG", "notes": ""},
        ],
        "status": "CREATED",
    },
]


def seed():
    db = SessionLocal()

    # Find an admin user to assign as creator
    admin = db.query(User).filter(User.role.in_(["ADMIN", "SUPER_ADMIN"])).first()
    if not admin:
        print("No admin user found. Run the main seed first.")
        db.close()
        return

    # Find customers to assign orders to
    customers = db.query(Customer).limit(3).all()
    if not customers:
        print("No customers found. Run the main seed first.")
        db.close()
        return

    import uuid
    from datetime import datetime, UTC

    created = 0
    for i, sample in enumerate(SAMPLE_ORDERS):
        customer = customers[i % len(customers)]
        code_suffix = uuid.uuid4().hex[:4].upper()
        code = f"TEST-{datetime.now(UTC).strftime('%Y%m')}-{code_suffix}"

        order = Order(
            order_code=code,
            customer_id=customer.id,
            product_name=sample["product_name"],
            quantity=sum(p["quantity"] for p in sample["products"]),
            unit="KG",
            shipment_status=sample["status"],
            expected_dispatch_date=date.today() + timedelta(days=30),
            expected_delivery_date=date.today() + timedelta(days=60),
            notes="Multi-product test order",
            created_by=admin.id,
        )
        db.add(order)
        db.flush()

        # Add order_products
        for p in sample["products"]:
            db.add(OrderProduct(
                order_id=order.id,
                product_name=p["product_name"],
                quantity=p["quantity"],
                unit=p["unit"],
                notes=p["notes"] or None,
            ))

        # Initialize milestones
        try:
            initialize_all_milestones(order_id=order.id, current_user=admin, db=db, commit=False)
        except Exception as e:
            print(f"  Milestone init skipped: {e}")

        db.flush()
        print(f"  Created {code} — {order.product_name} ({len(sample['products'])} products) for {customer.company_name}")
        created += 1

    db.commit()
    db.close()
    print(f"\nDone. {created} multi-product test orders created.")


if __name__ == "__main__":
    seed()
