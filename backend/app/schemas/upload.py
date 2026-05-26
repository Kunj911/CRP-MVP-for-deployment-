"""
app/schemas/upload.py

Pydantic schemas for the Upload module.

Covers:
  - Photo (media_files table): PROCUREMENT_IMAGE, PACKAGING_IMAGE, QA_IMAGE, LOADING_IMAGE
  - Document (documents table): INVOICE, BL_COPY, COA, PHYTOSANITARY_CERTIFICATE, LAB_REPORT, PACKING_LIST, OTHER
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Media type enum (matches media_files SQL ENUM) ────────────────────────────

class MediaType(str, Enum):
    PROCUREMENT_IMAGE = "PROCUREMENT_IMAGE"
    PACKAGING_IMAGE   = "PACKAGING_IMAGE"
    QA_IMAGE          = "QA_IMAGE"
    LOADING_IMAGE     = "LOADING_IMAGE"


# ── Document type enum (matches documents SQL ENUM) ───────────────────────────

class DocumentType(str, Enum):
    INVOICE                  = "INVOICE"
    BL_COPY                  = "BL_COPY"
    COA                      = "COA"
    PHYTOSANITARY_CERTIFICATE = "PHYTOSANITARY_CERTIFICATE"
    LAB_REPORT               = "LAB_REPORT"
    PACKING_LIST             = "PACKING_LIST"
    OTHER                    = "OTHER"


# ── Response schemas ──────────────────────────────────────────────────────────

class MediaFileResponse(BaseModel):
    """Returned after a successful photo upload or in media list."""
    id: int
    order_id: int
    milestone_id: Optional[int]
    media_type: MediaType
    file_name: Optional[str]
    file_url: str
    uploaded_by: Optional[int]
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    """Returned after a successful document upload or in document list."""
    id: int
    order_id: int
    document_type: DocumentType
    file_name: Optional[str]
    file_url: str
    uploaded_by: Optional[int]
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class UploadSummary(BaseModel):
    """
    Summary returned after any upload — includes storage path and size info.
    Wraps the full file response with extra metadata.
    """
    file_id: int
    file_url: str
    original_filename: str
    stored_filename: str
    size_bytes: int
    was_compressed: bool
    message: str
