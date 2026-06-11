"""Debug timeline & milestone data."""
import requests

BASE = "https://backend-production-3b9b2.up.railway.app/api/v1"

s = requests.Session()
r = s.post(f"{BASE}/auth/login", json={
    "email": "kunjalpesh@gmail.com",
    "password": "Iamtheadmin@1234"
})
token = r.json()["access_token"]
csrf = s.cookies.get("csrf_token")
s.headers.update({"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf or ""})

# Check timeline
r = s.get(f"{BASE}/orders/64/timeline")
if r.status_code == 200:
    data = r.json()
    milestones = data.get("milestones", [])
    print(f"Total milestones: {len(milestones)}")
    for m in milestones:
        print(f"  id={m.get('id')} stage={m.get('stage_name','')} status={m.get('status','')} "
              f"completed={m.get('is_completed','')} active={m.get('is_active','')} "
              f"type={m.get('item_type','')}")
else:
    print(f"Timeline: {r.status_code} {r.text[:200]}")

# What test files exist?
import os
cwd = os.getcwd()
print(f"\nCWD: {cwd}")
for f in os.listdir(cwd):
    if "test" in f.lower() or f.endswith(".pdf") or f.endswith(".jpg"):
        size = os.path.getsize(os.path.join(cwd, f))
        print(f"  {f}: {size} bytes")

# Create a minimal PDF
with open("test_doc.pdf", "wb") as f:
    # Minimal valid PDF
    f.write(b"%PDF-1.4\n1 0 obj<<>>endobj\nxref\n0 1\n0000000000 65535 f \ntrailer<<>>\nstartxref\n0\n%%EOF")
print("Created test_doc.pdf")
import mimetypes
print(f"  MIME: {mimetypes.guess_type('test_doc.pdf')}")

# Test document upload with real PDF
with open("test_doc.pdf", "rb") as f:
    r = s.post(f"{BASE}/upload/document",
        data={"order_id": 64, "document_type": "invoice"},
        files={"file": ("test.pdf", f, "application/pdf")})
print(f"Doc upload: {r.status_code} {r.text[:200]}")
