"""Debug UAT — tests CSRF + refresh + upload flow against Railway."""
import requests
import sys

BASE = "https://backend-production-3b9b2.up.railway.app/api/v1"
PASS = "PASS"
FAIL = "FAIL"

s = requests.Session()

print("=== 1.1 Login ===")
r = s.post(f"{BASE}/auth/login", json={
    "email": "kunjalpesh@gmail.com",
    "password": "Iamtheadmin@1234"
})
print(f"  Status: {r.status_code}")
assert r.status_code == 200, f"Login failed: {r.text[:200]}"
token = r.json()["access_token"]
user = r.json().get("user", {})
print(f"  User: {user.get('email')} role={user.get('role')}")
csrf = s.cookies.get("csrf_token")
print(f"  CSRF: {csrf[:20] if csrf else 'MISSING'}...")
s.headers.update({"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf or ""})

print("\n=== 1.2 Refresh ===")
r = s.post(f"{BASE}/auth/refresh")
if r.status_code == 200:
    print(f"  Status: {r.status_code} OK")
    new_token = r.json()["access_token"]
    s.headers.update({"Authorization": f"Bearer {new_token}"})
    new_csrf = s.cookies.get("csrf_token")
    if new_csrf:
        s.headers.update({"X-CSRF-Token": new_csrf})
else:
    print(f"  Status: {r.status_code} {FAIL}")
    print(f"  Body: {r.text[:250]}")
    # Try with updated CSRF from login
    print("  -> Checking if CSRF mismatch...")

print("\n=== 2.x Orders ===")
r = s.get(f"{BASE}/orders", params={"page": 1, "per_page": 5})
if r.status_code == 200:
    orders = r.json().get("data", [])
    print(f"  Orders: {len(orders)} found")
    if orders:
        oid = orders[0]["id"]
        print(f"  Using order_id={oid}")

        # Photo upload
        print("\n=== 2.1 Photo Upload ===")
        try:
            with open("test_image.jpg", "rb") as f:
                r = s.post(f"{BASE}/upload/photo",
                    data={"order_id": oid, "media_type": "PROCUREMENT_IMAGE"},
                    files={"file": ("test_image.jpg", f, "image/jpeg")})
            status = PASS if r.status_code == 201 else FAIL
            print(f"  Status: {r.status_code} {status}")
            if r.status_code != 201:
                print(f"  Body: {r.text[:200]}")
        except FileNotFoundError:
            print("  SKIP: test_image.jpg missing")

        # Document upload
        print("\n=== 2.2 Document Upload ===")
        try:
            with open("test_doc.pdf", "rb") as f:
                r = s.post(f"{BASE}/upload/document",
                    data={"order_id": oid, "document_type": "invoice"},
                    files={"file": ("test.pdf", f, "application/pdf")})
            status = PASS if r.status_code == 201 else FAIL
            print(f"  Status: {r.status_code} {status}")
            if r.status_code != 201:
                print(f"  Body: {r.text[:200]}")
        except FileNotFoundError:
            print("  SKIP: test_doc.pdf missing")

        # Timeline
        print("\n=== 2.x Timeline ===")
        r = s.get(f"{BASE}/orders/{oid}/timeline")
        if r.status_code == 200:
            data = r.json()
            milestones = data.get("milestones", [])
            completed = [m for m in milestones if m.get("is_completed")]
            active = [m for m in milestones if m.get("is_active")]
            events = [m for m in milestones if m.get("item_type") == "event"]
            print(f"  {len(completed)} completed, {len(active)} active, {len(events)} events")
            for m in milestones[:5]:
                sn = m.get("stage_name", m.get("stage_label", "?"))
                st = m.get("status", "")
                print(f"    {sn}: {st}")

# QA tests
print("\n=== 3.x QA Role Tests ===")
s2 = requests.Session()
r = s2.post(f"{BASE}/auth/login", json={
    "email": "poonam.qa.fittree@gmail.com",
    "password": "QA@1234"
})
if r.status_code == 200:
    qa_token = r.json()["access_token"]
    qa_csrf = s2.cookies.get("csrf_token")
    s2.headers.update({"Authorization": f"Bearer {qa_token}", "X-CSRF-Token": qa_csrf or ""})
    print(f"  Login: {r.status_code} OK")

    # QA doc upload
    with open("test_doc.pdf", "rb") as f:
        r = s2.post(f"{BASE}/upload/document",
            data={"order_id": 64, "document_type": "invoice"},
            files={"file": ("test.pdf", f, "application/pdf")})
    status = PASS if r.status_code == 201 else FAIL
    print(f"  Doc upload: {r.status_code} {status}")
    if r.status_code != 201:
        print(f"    {r.text[:200]}")

    # QA photo upload
    with open("test_image.jpg", "rb") as f:
        r = s2.post(f"{BASE}/upload/photo",
            data={"order_id": 64, "media_type": "QA_IMAGE"},
            files={"file": ("test.jpg", f, "image/jpeg")})
    status = PASS if r.status_code == 201 else FAIL
    print(f"  Photo upload: {r.status_code} {status}")

    # QA delete (should be denied)
    r = s2.delete(f"{BASE}/documents/1")
    status = PASS if r.status_code == 403 else FAIL
    print(f"  Delete blocked: {r.status_code} {status}")
else:
    print(f"  Login FAILED: {r.status_code} {r.text[:200]}")

print("\n=== 3.x WAREHOUSE Tests ===")
s3 = requests.Session()
r = s3.post(f"{BASE}/auth/login", json={
    "email": "poonam.fittree@gmail.com",
    "password": "Warehouse@1234"
})
if r.status_code == 200:
    wh_token = r.json()["access_token"]
    wh_csrf = s3.cookies.get("csrf_token")
    s3.headers.update({"Authorization": f"Bearer {wh_token}", "X-CSRF-Token": wh_csrf or ""})
    print(f"  Login: {r.status_code} OK")

    with open("test_doc.pdf", "rb") as f:
        r = s3.post(f"{BASE}/upload/document",
            data={"order_id": 64, "document_type": "invoice"},
            files={"file": ("test.pdf", f, "application/pdf")})
    status = PASS if r.status_code == 403 else FAIL
    print(f"  Doc upload (should deny): {r.status_code} {status}")

print("\n=== 9.x Invalid File Type ===")
r = s.post(f"{BASE}/upload/photo",
    data={"order_id": 64, "media_type": "PROCUREMENT_IMAGE"},
    files={"file": ("evil.exe", b"MZ\x90\x00", "application/x-msdownload")})
status = PASS if r.status_code in (403, 400) else FAIL
print(f"  .exe rejected: {r.status_code} {status}")

print("\n=== No-Auth Check ===")
s4 = requests.Session()
r = s4.get(f"{BASE}/auth/me")
status = PASS if r.status_code == 401 else FAIL
print(f"  auth/me: {r.status_code} {status}")

print("\n=== DONE ===")
