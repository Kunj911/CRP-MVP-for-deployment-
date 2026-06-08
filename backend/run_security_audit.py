import os
import sys
import json
from datetime import datetime, date

# ── Mock python-magic for Windows support ──
class MockMagic:
    @staticmethod
    def from_buffer(header_bytes, mime=True):
        if header_bytes.startswith(b"%PDF"):
            return "application/pdf"
        elif header_bytes.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        elif header_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        elif header_bytes.startswith(b"RIFF") and b"WEBP" in header_bytes:
            return "image/webp"
        elif header_bytes.startswith(b"PK\x03\x04"):
            # Default to DOCX/XLSX openxml signature
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        return "application/octet-stream"

sys.modules["magic"] = MockMagic

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app
from app.database.connection import get_db
from app.models.user import User
from app.models.order import Order
from app.models.customer import Customer
from app.models.document import Document
from app.models.audit_log import AuditLog
from app.models.order_document_requirement import OrderDocumentRequirement

# Disable rate limiting for the test run
from app.core.limiter import limiter
limiter.enabled = False

client = TestClient(app)

results = {
    "metadata": {
        "timestamp": datetime.now().isoformat(),
        "runner": "FastAPI TestClient Dynamic Auditor",
        "env": "testing"
    },
    "summary": {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "score": 0
    },
    "tests": []
}

def record_test(name, passed, detail):
    results["summary"]["total"] += 1
    if passed:
        results["summary"]["passed"] += 1
    else:
        results["summary"]["failed"] += 1
    results["tests"].append({
        "name": name,
        "passed": passed,
        "detail": str(detail)
    })
    status_str = "PASS" if passed else "FAIL"
    print(f"[{status_str}] {name}: {detail}")

def run_audit():
    print("==============================================================")
    print("           CRP DYNAMIC SECURITY AUDIT RUNNER                  ")
    print("==============================================================")
    
    # ── Resolve Dynamic IDs from Database ───────────────────────────────────
    db = next(get_db())
    try:
        cust_a = db.query(Customer).filter(Customer.company_name.like("%McCormick%")).first()
        cust_a_id = cust_a.id if cust_a else 1
        
        cust_b = db.query(Customer).filter(Customer.company_name.like("%Olam%")).first()
        cust_b_id = cust_b.id if cust_b else 2
        
        order_a = db.query(Order).filter(Order.customer_id == cust_a_id).first()
        order_a_id = order_a.id if order_a else 1
        
        order_b = db.query(Order).filter(Order.customer_id == cust_b_id).first()
        order_b_id = order_b.id if order_b else 6
        
        doc_b = db.query(Document).join(Order).filter(Order.customer_id == cust_b_id).first()
        doc_b_id = doc_b.id if doc_b else 4
        
        print(f"Dynamic ID mapping: Customer A ID = {cust_a_id}, Customer B ID = {cust_b_id}")
        print(f"Dynamic ID mapping: Customer A Order = {order_a_id}, Customer B Order = {order_b_id}, Customer B Doc = {doc_b_id}")
    finally:
        db.close()

    # ── Credentials from seed data ──────────────────────────────────────────
    users = {
        "super_admin": {"email": "kunjalpesh@gmail.com", "password": "Iamtheadmin@1234"},
        "warehouse": {"email": "poonam.fittree@gmail.com", "password": "Warehouse@1234"},
        "qa": {"email": "poonam.qa.fittree@gmail.com", "password": "QA@1234"},
        "docs": {"email": "poonam.docs.fittree@gmail.com", "password": "Document@1234"},
        "customer_a": {"email": "kunj.fittree@gmail.com", "password": "Kunj@1234"}, # McCormick (customer_id = cust_a_id)
        "customer_b": {"email": "roominesh.fittree@gmail.com", "password": "Roomi@1234"} # Olam (customer_id = cust_b_id)
    }

    tokens = {}

    # ── PHASE 1: Authentications ─────────────────────────────────────────────
    print("\n--- PHASE 1: Authentications ---")
    for role, creds in users.items():
        res = client.post("/api/v1/auth/login", json=creds)
        if res.status_code == 200 and "access_token" in res.json():
            tokens[role] = res.json()["access_token"]
            record_test(f"Auth - Valid Login: {role.upper()}", True, "Token returned successfully")
        else:
            record_test(f"Auth - Valid Login: {role.upper()}", False, f"Status: {res.status_code}, Body: {res.text}")

    # Invalid Login
    res = client.post("/api/v1/auth/login", json={"email": users["super_admin"]["email"], "password": "wrong-password"})
    record_test("Auth - Invalid Password Login Rejected", res.status_code == 401, f"Status: {res.status_code}")

    # Missing Token
    res = client.get("/api/v1/auth/me")
    record_test("Auth - Missing Token Rejected", res.status_code == 401, f"Status: {res.status_code}")

    # Malformed Token
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer malformed-token-string"})
    record_test("Auth - Malformed Token Rejected", res.status_code == 401, f"Status: {res.status_code}")


    # ── PHASE 2: RBAC Matrix Checks ──────────────────────────────────────────
    print("\n--- PHASE 2: RBAC Checks ---")
    
    # Endpoint: GET /customers (List all customers) - Staff only
    res = client.get("/api/v1/customers", headers={"Authorization": f"Bearer {tokens['super_admin']}"})
    record_test("RBAC - GET /customers (Super Admin Allowed)", res.status_code == 200, f"Status: {res.status_code}")
    
    res = client.get("/api/v1/customers", headers={"Authorization": f"Bearer {tokens['customer_a']}"})
    record_test("RBAC - GET /customers (Customer Denied)", res.status_code == 403, f"Status: {res.status_code}")

    # Endpoint: GET /orders/dashboard/stats - Staff only
    res = client.get("/api/v1/orders/dashboard/stats", headers={"Authorization": f"Bearer {tokens['qa']}"})
    record_test("RBAC - GET /orders/dashboard/stats (QA Staff Allowed)", res.status_code == 200, f"Status: {res.status_code}")
    
    res = client.get("/api/v1/orders/dashboard/stats", headers={"Authorization": f"Bearer {tokens['customer_a']}"})
    record_test("RBAC - GET /orders/dashboard/stats (Customer Denied)", res.status_code == 403, f"Status: {res.status_code}")

    # Endpoint: DELETE /orders/{order_id}/cancel - Super Admin only
    # First, create a temporary order that is in CREATED status (so it is not shipped/delivered and can be canceled)
    temp_order_payload = {
        "customer_id": cust_a_id,
        "product_name": "Temp Cancel Test Product",
        "quantity": 10.0,
        "unit": "MT",
        "expected_dispatch_date": "2026-06-25",
        "expected_delivery_date": "2026-07-10",
        "notes": "Temporary order for RBAC cancel test"
    }
    
    temp_order_id = None
    if "super_admin" in tokens:
        res_create = client.post(
            "/api/v1/orders",
            json=temp_order_payload,
            headers={"Authorization": f"Bearer {tokens['super_admin']}"}
        )
        if res_create.status_code == 201:
            temp_order_id = res_create.json()["data"]["id"]
            
    cancel_target_id = temp_order_id if temp_order_id is not None else order_a_id

    res = client.delete(f"/api/v1/orders/{cancel_target_id}/cancel", headers={"Authorization": f"Bearer {tokens['warehouse']}"})
    record_test(f"RBAC - DELETE /orders/{cancel_target_id}/cancel (Warehouse Denied)", res.status_code == 403, f"Status: {res.status_code}")

    res = client.delete(f"/api/v1/orders/{cancel_target_id}/cancel", headers={"Authorization": f"Bearer {tokens['super_admin']}"})
    record_test(f"RBAC - DELETE /orders/{cancel_target_id}/cancel (Super Admin Allowed)", res.status_code == 200, f"Status: {res.status_code}")


    # ── PHASE 3: Client Isolation Testing ────────────────────────────────────
    print("\n--- PHASE 3: Client Isolation ---")
    
    # Customer A (McCormick) owns order_a_id. Customer B (Olam) owns order_b_id.
    # Customer A attempts to view Customer B order
    res = client.get(f"/api/v1/orders/{order_b_id}", headers={"Authorization": f"Bearer {tokens['customer_a']}"})
    record_test("Isolation - Customer A view Customer B Order (Denied/NotFound)", res.status_code == 404, f"Status: {res.status_code}")

    # Customer A attempts to view Customer B milestones
    res = client.get(f"/api/v1/orders/{order_b_id}/milestones", headers={"Authorization": f"Bearer {tokens['customer_a']}"})
    record_test("Isolation - Customer A view Customer B Milestones (Denied/NotFound)", res.status_code == 404, f"Status: {res.status_code}")

    # Customer A attempts to view Customer B timeline
    res = client.get(f"/api/v1/orders/{order_b_id}/timeline", headers={"Authorization": f"Bearer {tokens['customer_a']}"})
    record_test("Isolation - Customer A view Customer B Timeline (Denied/NotFound)", res.status_code == 404, f"Status: {res.status_code}")

    # Customer A attempts to view Customer B documents list
    res = client.get(f"/api/v1/orders/{order_b_id}/documents", headers={"Authorization": f"Bearer {tokens['customer_a']}"})
    record_test("Isolation - Customer A view Customer B Documents list (Denied/NotFound)", res.status_code == 404, f"Status: {res.status_code}")

    # Customer A attempts to view Customer B document metadata
    res = client.get(f"/api/v1/documents/{doc_b_id}", headers={"Authorization": f"Bearer {tokens['customer_a']}"})
    record_test("Isolation - Customer A view Customer B Doc Metadata (Denied/NotFound)", res.status_code == 404, f"Status: {res.status_code}")

    # Customer A attempts to download Customer B document file
    res = client.get(f"/api/v1/documents/{doc_b_id}/download", headers={"Authorization": f"Bearer {tokens['customer_a']}"})
    record_test("Isolation - Customer A download Customer B Document File (Denied/NotFound)", res.status_code == 404, f"Status: {res.status_code}")


    # ── PHASE 4: Document Vault Safety & Validation ─────────────────────────
    print("\n--- PHASE 4: Document Vault ---")
    
    # Upload a document as DOCS role for Order A (McCormick - Customer A)
    # FastAPI test client allows multipart file uploads via files parameter
    dummy_pdf = b"%PDF-1.4 dummy content"
    files = {"file": ("test_invoice.pdf", dummy_pdf, "application/pdf")}
    data = {
        "order_id": str(order_a_id),
        "document_type": "invoice"
    }
    
    res = client.post(
        "/api/v1/upload/document",
        files=files,
        data=data,
        headers={"Authorization": f"Bearer {tokens['docs']}"}
    )
    
    temp_doc_id = None
    if res.status_code == 201:
        temp_doc_id = res.json()["data"]["file_id"]
        record_test("Doc Vault - Upload Document as Docs Team (Allowed)", True, f"Uploaded temp document ID {temp_doc_id}")
        
        # Check metadata visibility as Customer A. Since it is status = "uploaded" and visibility = "internal", Customer A should be denied.
        res_view = client.get(f"/api/v1/documents/{temp_doc_id}", headers={"Authorization": f"Bearer {tokens['customer_a']}"})
        record_test("Doc Vault - Customer access internal document metadata (Denied)", res_view.status_code in (403, 404), f"Status: {res_view.status_code}")

        # Customer A should not be allowed to download it either.
        res_dl = client.get(f"/api/v1/documents/{temp_doc_id}/download", headers={"Authorization": f"Bearer {tokens['customer_a']}"})
        record_test("Doc Vault - Customer download internal document file (Denied)", res_dl.status_code in (403, 404), f"Status: {res_dl.status_code}")
    else:
        record_test("Doc Vault - Upload Document as Docs Team", False, f"Status: {res.status_code}, Body: {res.text}")


    # ── PHASE 5: End-to-End Workflow Validation ─────────────────────────────
    print("\n--- PHASE 5: End-to-End Workflow ---")
    
    # Step 1: Super Admin onboards a new customer company
    company_suffix = int(datetime.now().timestamp())
    new_company_email = f"test.client.{company_suffix}@fittree.com"
    new_company_name = f"Auto Test Corp {company_suffix}"
    
    onboard_data = {
        "company_name": new_company_name,
        "contact_person": "Workflow Test User",
        "email": new_company_email,
        "phone": "+919999900000",
        "country": "India",
        "address": "Dynamic workflow industrial area"
    }
    
    res = client.post(
        "/api/v1/customers",
        json=onboard_data,
        headers={"Authorization": f"Bearer {tokens['super_admin']}"}
    )
    
    new_customer_id = None
    if res.status_code == 201:
        new_customer_id = res.json()["data"]["id"]
        record_test("E2E - Super Admin Onboards Customer (Success)", True, f"Customer ID: {new_customer_id}")
    else:
        record_test("E2E - Super Admin Onboards Customer", False, f"Status: {res.status_code}, Body: {res.text}")

    if new_customer_id:
        # Step 2: Create a new order for this customer
        order_data = {
            "customer_id": new_customer_id,
            "product_name": "Premium Ground Cumin",
            "quantity": 4500.0,
            "unit": "KG",
            "expected_dispatch_date": "2026-06-20",
            "expected_delivery_date": "2026-07-05",
            "notes": "Urgent packaging required"
        }
        
        res = client.post(
            "/api/v1/orders",
            json=order_data,
            headers={"Authorization": f"Bearer {tokens['super_admin']}"}
        )
        
        new_order_id = None
        if res.status_code == 201:
            new_order_id = res.json()["data"]["id"]
            record_test("E2E - Create Order for Onboarded Customer (Success)", True, f"Order ID: {new_order_id}")
        else:
            record_test("E2E - Create Order for Onboarded Customer", False, f"Status: {res.status_code}, Body: {res.text}")

        if new_order_id:
            # Step 3: Bulk initialize milestones
            res = client.post(
                f"/api/v1/orders/{new_order_id}/milestones/bulk",
                headers={"Authorization": f"Bearer {tokens['super_admin']}"}
            )
            record_test("E2E - Bulk Initialize Milestones (Success)", res.status_code == 201, f"Status: {res.status_code}")

            # Step 4: Advance order status CREATED -> PROCUREMENT
            status_data = {
                "status": "PROCUREMENT",
                "notes": "Moving order to sourcing phase"
            }
            res = client.patch(
                f"/api/v1/orders/{new_order_id}/status",
                json=status_data,
                headers={"Authorization": f"Bearer {tokens['super_admin']}"}
            )
            record_test("E2E - Advance Status CREATED -> PROCUREMENT (Success)", res.status_code == 200, f"Status: {res.status_code}")

            # Step 5: Verify that audit logs are created in the DB
            db = next(get_db())
            try:
                logs = db.query(AuditLog).filter(AuditLog.order_id == new_order_id).all()
                record_test("E2E - Audit Log Generation Check", len(logs) > 0, f"Found {len(logs)} audit entries for order {new_order_id}")
                for log in logs:
                    print(f"  -> Audit entry: {log.action_type} - {log.description}")
            finally:
                db.close()

    # Cleanup temp doc
    if temp_doc_id:
        res = client.delete(
            f"/api/v1/documents/{temp_doc_id}",
            headers={"Authorization": f"Bearer {tokens['docs']}"}
        )
        print(f"Cleaned up temp document ID {temp_doc_id}: {res.status_code}")

    results["summary"]["score"] = int((results["summary"]["passed"] / results["summary"]["total"]) * 100)
    
    # Save results to json file
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "security_audit_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)
        
    print("\n==============================================================")
    print(f"Audit completed: {results['summary']['passed']}/{results['summary']['total']} passed")
    print(f"Staging Readiness Score: {results['summary']['score']}%")
    print(f"Full report written to: {report_path}")
    print("==============================================================")

if __name__ == "__main__":
    run_audit()
