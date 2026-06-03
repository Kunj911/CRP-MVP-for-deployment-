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
    invoice = "invoice"
    bill_of_lading = "bill_of_lading"
    lab_report = "lab_report"
    packing_list = "packing_list"
    certificate_of_analysis = "certificate_of_analysis"
    phytosanitary_certificate = "phytosanitary_certificate"
    product_specification = "product_specification"
    insurance_certificate = "insurance_certificate"
    purchase_order = "purchase_order"
    certificate_of_origin = "certificate_of_origin"
    other = "other"

    @classmethod
    def _missing_(cls, value):
        if not isinstance(value, str):
            return None
        val_lower = value.lower()
        legacy_map = {
            "bl_copy": "bill_of_lading",
            "coa": "certificate_of_analysis",
            "certificate": "phytosanitary_certificate",
        }
        mapped = legacy_map.get(val_lower, val_lower)
        for member in cls:
            if member.value == mapped:
                return member
        return None


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
    file_size: Optional[int] = None
    uploaded_by: Optional[int]
    uploaded_at: datetime
    status: str
    visibility: str
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    is_deleted: bool

    model_config = {"from_attributes": True}


class OrderDocumentRequirementResponse(BaseModel):
    id: int
    order_id: int
    document_type: DocumentType
    required: bool
    uploaded: bool
    approved: bool
    uploaded_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    document_id: Optional[int] = None

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
