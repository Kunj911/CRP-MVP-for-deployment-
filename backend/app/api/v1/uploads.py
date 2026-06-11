"""
app/api/v1/uploads.py

File upload route handlers — photos and documents.
All pipeline logic lives in app/services/upload_service.py.

Endpoints:
  POST   /api/v1/upload/photo                    → upload a photo
  POST   /api/v1/upload/document                 → upload a document
  GET    /api/v1/orders/{order_id}/media         → list media for order
  GET    /api/v1/orders/{order_id}/documents     → list documents for order
  DELETE /api/v1/media/{media_id}                → delete a photo
  DELETE /api/v1/documents/{doc_id}              → delete a document

Note: FastAPI handles multipart/form-data via UploadFile + Form().
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, File, Form, Query, UploadFile, Request, Header, HTTPException

from app.api.deps import CurrentUser, DbSession, PhotoUploaderUser, DocUploaderUser, MediaDeleterUser, DocDeleterUser
from app.core.limiter import limiter
from app.config.settings import get_settings
from app.schemas.common import SuccessResponse
from app.schemas.upload import (
    DocumentResponse,
    DocumentType,
    MediaFileResponse,
    MediaType,
    UploadSummary,
    OrderDocumentRequirementResponse,
)
from app.services import upload_service

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["Uploads"])


# ── POST /upload/photo ────────────────────────────────────────────────────────

@router.post(
    "/upload/photo",
    response_model=SuccessResponse[UploadSummary],
    status_code=201,
    summary="Upload a photo",
    description=(
        "Upload a procurement, packaging, QA, or loading image for an order.\n\n"
        "**Mobile-first**: Accepts JPEG, PNG, WebP, HEIC (iOS camera). "
        "HEIC files are auto-converted to JPEG. "
        "Images over 2MB are automatically compressed. "
        "EXIF metadata is stripped for privacy.\n\n"
        "**Allowed types**: JPEG, PNG, WebP, HEIC (max 10MB)\n\n"
        "**Storage path**: `{env}/orders/{order_id}/{media_type}/{uuid}.jpg`\n\n"
        "Requires ADMIN, WAREHOUSE, or QA role."
    ),
)
@limiter.limit("15/minute")
async def upload_photo(
    request: Request,
    current_user: PhotoUploaderUser,
    db: DbSession,
    file: UploadFile = File(..., description="Image file (JPEG/PNG/WebP/HEIC, max 10MB)"),
    content_length: int = Header(..., alias="content-length"),
    order_id: int = Form(..., gt=0, description="Order ID this photo belongs to"),
    media_type: MediaType = Form(..., description="Photo category"),
    milestone_id: Optional[int] = Form(
        None, gt=0, description="Optional: link photo to a specific milestone"
    ),
) -> SuccessResponse[UploadSummary]:
    if content_length > settings.MAX_PHOTO_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Photo file too large (max 10MB)")

    result = await upload_service.upload_photo(
        file=file,
        order_id=order_id,
        media_type=media_type,
        current_user=current_user,
        db=db,
        milestone_id=milestone_id,
    )
    return SuccessResponse(data=result, message=result.message)


# ── POST /upload/document ─────────────────────────────────────────────────────

@router.post(
    "/upload/document",
    response_model=SuccessResponse[UploadSummary],
    status_code=201,
    summary="Upload a shipment document",
    description=(
        "Upload a shipment document (Invoice, BL Copy, COA, Phytosanitary Certificate, etc.)\n\n"
        "**Allowed types**: PDF, XLSX, DOCX (max 25MB)\n\n"
        "Documents are stored as-is (no compression).\n\n"
        "**Storage path**: `{env}/orders/{order_id}/documents/{uuid}.pdf`\n\n"
        "Requires ADMIN or DOCUMENTATION team role."
    ),
)
@limiter.limit("10/minute")
async def upload_document(
    request: Request,
    current_user: DocUploaderUser,
    db: DbSession,
    file: UploadFile = File(..., description="Document file (PDF/XLSX/DOCX, max 25MB)"),
    content_length: int = Header(..., alias="content-length"),
    order_id: int = Form(..., gt=0, description="Order ID this document belongs to"),
    document_type: DocumentType = Form(..., description="Document category"),
) -> SuccessResponse[UploadSummary]:
    if content_length > settings.MAX_DOCUMENT_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Document file too large (max 25MB)")

    result = await upload_service.upload_document(
        file=file,
        order_id=order_id,
        document_type=document_type,
        current_user=current_user,
        db=db,
    )
    return SuccessResponse(data=result, message=result.message)


# ── GET /orders/{order_id}/media ──────────────────────────────────────────────

@router.get(
    "/orders/{order_id}/media",
    response_model=SuccessResponse[List[MediaFileResponse]],
    summary="List media files for an order",
    description=(
        "Returns all uploaded photos for an order, sorted by upload time (newest first). "
        "Filter by media_type to get only QA images, packaging photos, etc. "
        "CUSTOMER role can only access their own orders' media."
    ),
)
def list_order_media(
    order_id: int,
    current_user: CurrentUser,
    db: DbSession,
    media_type: Optional[MediaType] = Query(
        None, description="Filter by photo category"
    ),
) -> SuccessResponse[List[MediaFileResponse]]:
    media = upload_service.get_order_media(
        order_id=order_id,
        current_user=current_user,
        db=db,
        media_type=media_type,
    )
    return SuccessResponse(
        data=media,
        message=f"{len(media)} file(s) found for order {order_id}",
    )


# ── GET /orders/{order_id}/documents ─────────────────────────────────────────

@router.get(
    "/orders/{order_id}/documents",
    response_model=SuccessResponse[List[DocumentResponse]],
    summary="List documents for an order",
    description=(
        "Returns all shipment documents for an order (Document Vault). "
        "Filter by document_type to get only invoices, BL copies, etc. "
        "CUSTOMER role can only access documents for their own orders."
    ),
)
def list_order_documents(
    order_id: int,
    current_user: CurrentUser,
    db: DbSession,
    document_type: Optional[DocumentType] = Query(
        None, description="Filter by document type"
    ),
) -> SuccessResponse[List[DocumentResponse]]:
    docs = upload_service.get_order_documents(
        order_id=order_id,
        current_user=current_user,
        db=db,
        document_type=document_type,
    )
    return SuccessResponse(
        data=docs,
        message=f"{len(docs)} document(s) found for order {order_id}",
    )


# ── GET /orders/{order_id}/document-checklist ─────────────────────────────────

@router.get(
    "/orders/{order_id}/document-checklist",
    response_model=SuccessResponse[List[OrderDocumentRequirementResponse]],
    summary="Get document checklist for an order",
    description="Returns the structured documentation checklist requirements for an order."
)
def get_order_checklist(
    order_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[List[OrderDocumentRequirementResponse]]:
    checklist = upload_service.get_order_document_checklist(
        order_id=order_id,
        current_user=current_user,
        db=db,
    )
    return SuccessResponse(
        data=checklist,
        message=f"{len(checklist)} checklist items found for order {order_id}",
    )


# ── DELETE /media/{media_id} ──────────────────────────────────────────────────

@router.delete(
    "/media/{media_id}",
    response_model=SuccessResponse[str],
    summary="Delete a media file",
    description=(
        "Permanently deletes a photo from both the database and storage backend. "
        "Requires ADMIN or SUPER_ADMIN role."
    ),
)
def delete_media(
    media_id: int,
    current_user: MediaDeleterUser,
    db: DbSession,
) -> SuccessResponse[str]:
    upload_service.delete_media_file(
        media_id=media_id,
        current_user=current_user,
        db=db,
    )
    return SuccessResponse(
        data=str(media_id),
        message=f"Media file {media_id} deleted successfully",
    )


# ── DELETE /documents/{doc_id} ────────────────────────────────────────────────

@router.delete(
    "/documents/{doc_id}",
    response_model=SuccessResponse[str],
    summary="Delete a document",
    description=(
        "Soft-deletes a document by setting is_deleted = True and resetting the order "
        "document requirement state. Requires ADMIN, SUPER_ADMIN, or DOCUMENTATION team role."
    ),
)
def delete_document(
    doc_id: int,
    current_user: DocDeleterUser,
    db: DbSession,
) -> SuccessResponse[str]:
    upload_service.delete_document(
        doc_id=doc_id,
        current_user=current_user,
        db=db,
    )
    return SuccessResponse(
        data=str(doc_id),
        message=f"Document {doc_id} deleted successfully",
    )

