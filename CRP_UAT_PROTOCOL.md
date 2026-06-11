# CRP UAT Protocol — User Acceptance Testing

## Prerequisites

- Railway backend accessible at `https://backend-production-3b9b2.up.railway.app`
- Frontend accessible or API tested via `curl`/Postman
- Test accounts for each role (see seed data in `admin.py` lines 87-91)

## Seed Credentials

| Role | Email | Password |
|------|-------|----------|
| SUPER_ADMIN | kunjalpesh@gmail.com | Iamtheadmin@1234 |
| WAREHOUSE | poonam.fittree@gmail.com | Warehouse@1234 |
| QA | poonam.qa.fittree@gmail.com | QA@1234 |
| DOCUMENTATION | poonam.docs.fittree@gmail.com | Document@1234 |
| CUSTOMER | kunj.fittree@gmail.com | Kunj@1234 |

---

## Area 1 — Authentication Validation

### 1.1 Login

| # | Test | Steps | Expected | Result |
|---|------|-------|----------|--------|
| 1.1.1 | Valid Login | `POST /auth/login` with valid creds | 200 + access_token + refresh cookie | ⬜ |
| 1.1.2 | Invalid Login | `POST /auth/login` with wrong password | 401 Unauthorized | ⬜ |
| 1.1.3 | Expired token | Use expired JWT in Authorization header | 401 Unauthorized | ⬜ |
| 1.1.4 | Deactivated user | Login as a deactivated user (after Area 5.3) | 401 "deactivated" | ⬜ |

### 1.2 Session Stability

| # | Test | Steps | Expected | Result |
|---|------|-------|----------|--------|
| 1.2.1 | Refresh browser | Login → refresh page → check `/auth/me` | Still authenticated | ⬜ |
| 1.2.2 | Multiple tabs | Login in Tab A → open Tab B → same session | Both tabs authenticated | ⬜ |
| 1.2.3 | Token refresh | Wait 15min → upload a file | Upload succeeds (auto-refresh) | ⬜ |

### 1.3 Upload Session Stability

| # | Test | Steps | Expected | Result |
|---|------|-------|----------|--------|
| 1.3.1 | Single upload | Upload 1 PDF | 201, no logout | ⬜ |
| 1.3.2 | 5 sequential uploads | Upload 5 PDFs one after another | All 201, no session loss | ⬜ |
| 1.3.3 | 10 sequential uploads | Upload 10 mixed files | All succeed, no 401 | ⬜ |
| 1.3.4 | Mixed types | Photo → Document → Photo → Document | All 201 | ⬜ |

---

## Area 2 — Milestone Synchronization

### 2.1 Photo → Milestone

| # | Media Type | Milestone Stage | Test |
|---|-----------|----------------|------|
| 2.1.1 | PROCUREMENT_IMAGE | PROCUREMENT | Upload → verify milestone COMPLETED |
| 2.1.2 | QA_IMAGE | QA_TESTING | Upload → verify milestone COMPLETED |
| 2.1.3 | PACKAGING_IMAGE | PACKAGING_COMPLETED | Upload → verify milestone COMPLETED |
| 2.1.4 | LOADING_IMAGE | CONTAINER_LOADING | Upload → verify milestone COMPLETED |

**Steps for each:**
1. Find an order where the target milestone is PENDING or IN_PROGRESS
2. Upload a photo with the matching `media_type`
3. `GET /orders/{id}/timeline` and verify milestone status = COMPLETED
4. Verify `completed_at` timestamp is populated
5. Verify `completed_by` matches the uploading user

### 2.2 Document → Milestone

| # | Test | Steps | Expected | Result |
|---|------|-------|----------|--------|
| 2.2.1 | Document upload | Upload any document type | DOCUMENTS_UPLOADED milestone → COMPLETED | ⬜ |
| 2.2.2 | Document approval | Approve the document | DOCUMENTS_UPLOADED stays COMPLETED (belt-and-suspenders) | ⬜ |
| 2.2.3 | Auto-advance | Complete a non-terminal milestone | Next milestone → IN_PROGRESS | ⬜ |

### 2.3 Deletion → Milestone

| # | Test | Steps | Expected | Result |
|---|------|-------|----------|--------|
| 2.3.1 | Photo deletion | Delete a photo | OrderEvent `media_deleted` created; milestone NOT reverted | ⬜ |
| 2.3.2 | Document deletion | Delete a non-approved document | OrderEvent `document_deleted` created; milestone NOT reverted | ⬜ |

---

## Area 3 — QA Role Validation

### 3.1 Allowed Operations

| # | Operation | Steps | Expected | Result |
|---|-----------|-------|----------|--------|
| 3.1.1 | Upload document | Login as QA → upload PDF | 201 Created | ⬜ |
| 3.1.2 | Upload photo | Login as QA → upload image | 201 Created | ⬜ |
| 3.1.3 | View document vault | `GET /orders/{id}/documents` | 200 with document list | ⬜ |
| 3.1.4 | View photo gallery | `GET /orders/{id}/media` | 200 with media list | ⬜ |
| 3.1.5 | Approve document | `POST /documents/{id}/approve` | 200 Approved | ⬜ |
| 3.1.6 | Reject document | `POST /documents/{id}/reject` | 200 Rejected | ⬜ |

### 3.2 Denied Operations

| # | Operation | Steps | Expected | Result |
|---|-----------|-------|----------|--------|
| 3.2.1 | Delete approved document | `DELETE /documents/{id}` where status=approved | 403 Forbidden | ⬜ |
| 3.2.2 | Delete unapproved document | `DELETE /documents/{id}` where status≠approved | 403 Forbidden | ⬜ |
| 3.2.3 | Delete photo | `DELETE /media/{id}` | 403 Forbidden | ⬜ |
| 3.2.4 | Cancel order | `PATCH /orders/{id}/status` → CANCELLED | 403 Forbidden | ⬜ |
| 3.2.5 | Deactivate user | `POST /admin/users/deactivate` | 403 Forbidden | ⬜ |
| 3.2.6 | Access document tab in UI | (Frontend) Load UploadPage | Photo tab only (no Document tab) | ⬜ |

---

## Area 4 — Admin Asset Management

### 4.1 Deletion

| # | Test | Steps | Expected | Result |
|---|------|-------|----------|--------|
| 4.1.1 | Delete unapproved doc | Login as ADMIN → `DELETE /documents/{id}` | 200, soft-deleted | ⬜ |
| 4.1.2 | Delete approved doc | `DELETE /documents/{id}` where status=approved | 200, ADMIN bypass OK | ⬜ |
| 4.1.3 | Delete photo | `DELETE /media/{id}` | 200, hard-deleted | ⬜ |
| 4.1.4 | Confirmation modal | (Frontend) Click delete icon | Modal shows asset name/type/date/status | ⬜ |
| 4.1.5 | Audit log created | Check audit_logs table after deletion | Entry exists with verification_status, deleted_by_role | ⬜ |
| 4.1.6 | Storage cleaned | Check storage backend after deletion | File no longer exists | ⬜ |
| 4.1.7 | OrderEvent created | `GET /orders/{id}/timeline` after deletion | Event type = document_deleted or media_deleted | ⬜ |

### 4.2 Cancel Order

| # | Test | Steps | Expected | Result |
|---|------|-------|----------|--------|
| 4.2.1 | Cancel CREATED order | `PATCH /orders/{id}/status` → CANCELLED | 200, status=CANCELLED | ⬜ |
| 4.2.2 | Cancel SHIPPED order | `PATCH /orders/{id}/status` → CANCELLED | 400 "Invalid transition" | ⬜ |
| 4.2.3 | Cancel DELIVERED order | Same | 400 | ⬜ |

---

## Area 5 — Super Admin Validation

| # | Test | Steps | Expected | Result |
|---|------|-------|----------|--------|
| 5.1 | Delete approved doc (any order) | `DELETE /documents/{id}` across different projects | 200, all succeed | ⬜ |
| 5.2 | Delete photo (any order) | `DELETE /media/{id}` across different orders | 200, all succeed | ⬜ |
| 5.3 | Deactivate user | `POST /admin/users/deactivate` with user_id | 200, user disabled | ⬜ |
| 5.4 | Deactivate another SUPER_ADMIN | Same with another SUPER_ADMIN's user_id | 403 Forbidden | ⬜ |
| 5.5 | Reactivate user | `POST /admin/users/deactivate` with deactivate=false | 200, user re-enabled | ⬜ |

---

## Area 6 — Upload Validation Matrix

| # | File Type | Size | Count | Expected | Result |
|---|-----------|------|-------|----------|--------|
| 6.1 | JPEG photo | < 1MB | 1 | 201 | ⬜ |
| 6.2 | JPEG photo | > 5MB | 1 | 201 (compressed) | ⬜ |
| 6.3 | PNG photo | ~2MB | 1 | 201 | ⬜ |
| 6.4 | PDF document | < 1MB | 1 | 201 | ⬜ |
| 6.5 | PDF document | ~10MB | 1 | 201 | ⬜ |
| 6.6 | DOCX document | ~2MB | 1 | 201 | ⬜ |
| 6.7 | XLSX document | ~1MB | 1 | 201 | ⬜ |
| 6.8 | Sequential uploads | Mixed | 10 | All 201, no duplicates | ⬜ |
| 6.9 | Oversize photo | > 10MB | 1 | 413 Too Large | ⬜ |
| 6.10 | Oversize document | > 25MB | 1 | 413 Too Large | ⬜ |

---

## Area 7 — Database Validation

Run these queries manually or via the test script:

```sql
-- 7.1: Upload records created
SELECT COUNT(*) FROM media_files WHERE order_id = <id>;
SELECT COUNT(*) FROM documents WHERE order_id = <id> AND is_deleted = FALSE;

-- 7.2: Audit records created
SELECT * FROM audit_logs WHERE target_table = 'media_files' ORDER BY created_at DESC LIMIT 5;
SELECT * FROM audit_logs WHERE target_table = 'documents' AND action_type = 'DELETE' ORDER BY created_at DESC LIMIT 5;

-- 7.3: Milestone records updated
SELECT stage_name, status, completed_at, completed_by
FROM milestones
WHERE order_id = <id>
ORDER BY CASE stage_name
  WHEN 'PROCUREMENT' THEN 1 WHEN 'RAW_MATERIAL_VERIFIED' THEN 2
  WHEN 'QA_TESTING' THEN 3 WHEN 'PACKAGING_STARTED' THEN 4
  WHEN 'PACKAGING_COMPLETED' THEN 5 WHEN 'DOCUMENTS_UPLOADED' THEN 6
  WHEN 'CONTAINER_LOADING' THEN 7 WHEN 'SHIPMENT_DISPATCHED' THEN 8
  WHEN 'DELIVERED' THEN 9 ELSE 99 END;

-- 7.4: Foreign keys preserved
SELECT m.order_id, o.order_id FROM media_files m LEFT JOIN orders o ON m.order_id = o.order_id WHERE o.order_id IS NULL;
-- Should return 0 rows (no orphaned media)

SELECT d.order_id, o.order_id FROM documents d LEFT JOIN orders o ON d.order_id = o.order_id WHERE o.order_id IS NULL;
-- Should return 0 rows (no orphaned documents)
```

---

## Area 8 — Storage Validation

| # | Test | Steps | Expected | Result |
|---|------|-------|----------|--------|
| 8.1 | Upload → file exists | Check LOCAL_UPLOAD_DIR or S3 bucket | File present at correct path | ⬜ |
| 8.2 | Delete → file removed | Delete via API → check storage | File absent | ⬜ |
| 8.3 | Replace → old removed, new exists | Upload, delete, re-upload | Only new file present | ⬜ |
| 8.4 | Metadata correct | Check `file_url`, `storage_key`, `file_size` in DB | Match storage backend | ⬜ |

---

## Area 9 — Error Handling

| # | Test | Steps | Expected | Result |
|---|------|-------|----------|--------|
| 9.1 | Invalid file type | Upload `.exe` as document | 403 "Invalid document type" | ⬜ |
| 9.2 | Oversize file | Upload 15MB photo | 413 "Photo file too large" | ⬜ |
| 9.3 | Missing auth | Call upload without Authorization header | 401 Unauthorized | ⬜ |
| 9.4 | Wrong role | WAREHOUSE tries document upload | 403 Forbidden | ⬜ |
| 9.5 | Network failure | Disconnect mid-upload | No crash, no partial record | ⬜ |
| 9.6 | Empty file | Upload 0-byte file | 400 or 413 (size validation) | ⬜ |

---

## Results Summary

| Area | Pass | Fail | Blocked | Coverage % |
|------|------|------|---------|------------|
| 1. Authentication | ⬜ | ⬜ | ⬜ | ⬜ |
| 2. Milestones | ⬜ | ⬜ | ⬜ | ⬜ |
| 3. QA RBAC | ⬜ | ⬜ | ⬜ | ⬜ |
| 4. Admin Deletion | ⬜ | ⬜ | ⬜ | ⬜ |
| 5. Super Admin | ⬜ | ⬜ | ⬜ | ⬜ |
| 6. Upload Matrix | ⬜ | ⬜ | ⬜ | ⬜ |
| 7. Database | ⬜ | ⬜ | ⬜ | ⬜ |
| 8. Storage | ⬜ | ⬜ | ⬜ | ⬜ |
| 9. Error Handling | ⬜ | ⬜ | ⬜ | ⬜ |
| **Total** | ⬜ | ⬜ | ⬜ | ⬜ |

**Critical Path Verdict:** ⬜ PASS / ⬜ FAIL / ⬜ BLOCKED

---

## curl-Based Smoke Tests

These can be run from any machine with network access to the backend.

```bash
# ── Config ──
BASE=https://backend-production-3b9b2.up.railway.app/api/v1

# ── 1. Login as ADMIN ──
curl -s -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"kunjalpesh@gmail.com","password":"Iamtheadmin@1234"}' \
  -c cookies.txt > login.json
TOKEN=$(cat login.json | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "TOKEN=$TOKEN"

# ── 2. Verify session ──
curl -s "$BASE/auth/me" -H "Authorization: Bearer $TOKEN" | python -m json.tool

# ── 3. Upload a photo ──
curl -s -X POST "$BASE/upload/photo" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test_image.jpg" \
  -F "order_id=1" \
  -F "media_type=PROCUREMENT_IMAGE"

# ── 4. Upload a document ──
curl -s -X POST "$BASE/upload/document" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test_doc.pdf" \
  -F "order_id=1" \
  -F "document_type=invoice"

# ── 5. Check milestones ──
curl -s "$BASE/orders/1/timeline" -H "Authorization: Bearer $TOKEN" | python -c "
import sys, json
data = json.load(sys.stdin)
for m in data.get('milestones', []):
    print(f\"{m['stage_label']}: {m['status']}\")
"

# ── 6. QA upload (login first) ──
# ... (repeat login as QA, then try document upload)

# ── 7. Delete a document (login as ADMIN) ──
curl -s -X DELETE "$BASE/documents/1" -H "Authorization: Bearer $TOKEN"

# ── 8. Verify deletion audit ──
curl -s "$BASE/orders/1/timeline" -H "Authorization: Bearer $TOKEN" | python -c "
import sys, json
data = json.load(sys.stdin)
events = [m for m in data.get('milestones', []) if m.get('item_type') == 'event']
for e in events:
    print(f\"{e['stage_label']}: {e['remarks']}\")
"
```

---

## Defect Reporting Template

```
## DEFECT-<NUMBER>

**Area:** (Auth / Milestones / RBAC / Deletion / Upload / Storage / Error)
**Severity:** (Critical / Major / Minor / Cosmetic)
**Environment:** (Railway / Local)

**Steps to Reproduce:**
1.
2.
3.

**Expected:**
**Actual:**
**Evidence:** (screenshot / curl output / server log)

**Root Cause:** (leave blank for dev team)
**Fix:** (leave blank for dev team)
```
