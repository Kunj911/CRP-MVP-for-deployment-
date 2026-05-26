"""
app/api/v1/documents.py

Document Vault route handlers.
Provides secure document downloads with audit logging and role-based access.
"""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, RedirectResponse

from app.api.deps import CurrentUser, DbSession
from app.services import document_vault_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Document Vault"])


# ── GET /documents/{doc_id}/download ──────────────────────────────────────────

@router.get(
    "/documents/{doc_id}/download",
    summary="Securely download a document",
    description=(
        "Download a document from the vault.\n\n"
        "**Access Rules**:\n"
        "- CUSTOMER can only download documents linked to their own orders.\n"
        "- ADMIN, WAREHOUSE, QA, and DOCUMENTATION can download any document.\n\n"
        "**Features**:\n"
        "- JWT validation required.\n"
        "- Automatically logs the download action in the audit logs.\n"
        "- If storage is local, securely streams the file using FastAPI FileResponse.\n"
        "- If storage is external (S3), redirects to the secure URL."
    ),
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
    
    # If the file is stored locally, serve it directly and securely via FileResponse
    # This avoids exposing a public static directory.
    if is_local:
        return FileResponse(
            path=path_or_url,
            filename=doc.file_name or f"document_{doc.id}.pdf",
            media_type="application/octet-stream",
            content_disposition_type="attachment"
        )
    
    # If the file is stored remotely (S3 / Cloudinary), redirect the user
    # to the secure URL (which could be a presigned URL in production).
    return RedirectResponse(url=path_or_url, status_code=307)
