"""
app/api/v1/documents.py

Document Vault route handlers.
Provides secure document downloads, details, approval, and rejection.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Body
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DbSession
from app.services import document_vault_service
from app.services import upload_service
from app.schemas.upload import DocumentResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Document Vault"])


class RejectionRequest(BaseModel):
    remarks: str = Field(..., min_length=1, description="Reason for rejection")


# ── GET /documents/vault — list all documents with order info (single query, no N+1) ──

@router.get(
    "/documents/vault",
    summary="List all documents with order info for the document vault",
)
def list_document_vault(
    current_user: CurrentUser,
    db: DbSession,
):
    """Return all non-deleted documents joined with order metadata in one query."""
    from app.models.document import Document
    from app.models.order import Order
    from app.models.customer import Customer
    from app.core.exceptions import NotFoundException
    
    query = (
        db.query(
            Document.id,
            Document.order_id,
            Order.order_code,
            Customer.company_name,
            Order.product_name,
            Document.document_type,
            Document.file_name,
            Document.file_url,
            Document.file_size,
            Document.status,
            Document.visibility,
            Document.uploaded_by,
            Document.uploaded_at,
            Document.reviewed_by,
            Document.reviewed_at,
        )
        .join(Order, Document.order_id == Order.id)
        .join(Customer, Order.customer_id == Customer.id)
        .filter(Document.is_deleted == False)
    )

    if current_user.role == "CUSTOMER":
        query = query.filter(
            Document.status == "approved",
            Document.visibility == "customer_visible",
        )

    rows = query.all()

    result = []
    for r in rows:
        result.append({
            "id": r.id,
            "order_id": r.order_id,
            "order_code": r.order_code,
            "customer_name": r.company_name or "N/A",
            "commodity_name": r.product_name or "N/A",
            "document_type": r.document_type,
            "file_name": r.file_name,
            "file_url": r.file_url,
            "file_size": r.file_size,
            "status": r.status,
            "visibility": r.visibility,
            "uploaded_by": r.uploaded_by,
            "uploaded_at": r.uploaded_at.isoformat() if r.uploaded_at else None,
            "reviewed_by": r.reviewed_by,
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
        })

    return {"data": result}


# ── GET /documents/{doc_id} ───────────────────────────────────────────────────

@router.get(
    "/documents/{doc_id}",
    summary="Get document details",
    response_model=DocumentResponse
)
def get_document(
    doc_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    """Retrieve metadata of a single document with proper role scoping."""
    from app.models.document import Document
    from app.core.exceptions import NotFoundException, ForbiddenException
    
    doc = db.query(Document).filter(Document.id == doc_id, Document.is_deleted == False).first()
    if not doc:
        raise NotFoundException("Document", doc_id)
        
    # Customer scoping: must own order and document must be approved/visible
    if current_user.role == "CUSTOMER":
        if doc.order.customer_id != current_user.customer_id:
            raise NotFoundException("Document", doc_id)
        if doc.status != "approved" or doc.visibility != "customer_visible":
            raise ForbiddenException("You do not have access to this document")
            
    return doc


# ── GET /documents/{doc_id}/download ──────────────────────────────────────────

@router.get(
    "/documents/{doc_id}/download",
    summary="Securely download a document",
    responses={
        200: {"description": "File downloaded successfully"},
        307: {"description": "Redirected to external secure storage URL"},
        403: {"description": "Forbidden - You do not have permission to download this document"},
        404: {"description": "Document not found"},
    }
)
def download_document(
    doc_id: int,
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
):
    ip = request.client.host if request.client else None
    doc, path_or_url, is_local = document_vault_service.get_document_for_download(
        doc_id=doc_id,
        current_user=current_user,
        db=db,
        ip_address=ip,
    )
    
    if is_local:
        return FileResponse(
            path=path_or_url,
            filename=doc.file_name or f"document_{doc.id}.pdf",
            media_type="application/octet-stream",
            content_disposition_type="attachment"
        )
    if not is_local:
        from urllib.parse import urlparse
        from app.core.exceptions import ForbiddenException
        from app.core.config import get_settings
        settings = get_settings()
        parsed_url = urlparse(path_or_url)
        if parsed_url.netloc:
            netloc = parsed_url.netloc.lower()
            is_allowed = False
            allowed_domains = settings.REDIRECT_DOMAINS
            for domain in allowed_domains:
                if netloc == domain or netloc.startswith(domain + ":"):
                    is_allowed = True
                    break
            if "amazonaws.com" in netloc:
                is_allowed = True
            if "cloudinary.com" in netloc:
                is_allowed = True
            if not is_allowed:
                raise ForbiddenException(f"Redirect target domain '{parsed_url.netloc}' is not whitelisted for secure download.")
        
        return RedirectResponse(url=path_or_url, status_code=307)


# ── POST /documents/{doc_id}/approve ──────────────────────────────────────────

@router.post(
    "/documents/{doc_id}/approve",
    summary="Approve a document checklist item",
    response_model=DocumentResponse
)
def approve_doc(
    doc_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    """Approve a document and update checklist status. (Admin/QA only)."""
    return upload_service.approve_document(doc_id=doc_id, current_user=current_user, db=db)


# ── POST /documents/{doc_id}/reject ───────────────────────────────────────────

@router.post(
    "/documents/{doc_id}/reject",
    summary="Reject a document checklist item",
    response_model=DocumentResponse
)
def reject_doc(
    doc_id: int,
    req: RejectionRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    """Reject a document with remarks and trigger notifications. (Admin/QA only)."""
    return upload_service.reject_document(
        doc_id=doc_id,
        remarks=req.remarks,
        current_user=current_user,
        db=db
    )
