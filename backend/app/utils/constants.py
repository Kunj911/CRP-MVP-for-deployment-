"""
app/utils/constants.py

Application-wide enums and constants.
These are the single source of truth for all categorical values.
"""

from enum import Enum


# ── User Roles ────────────────────────────────────────────────────────────────

class UserRole(str, Enum):
    ADMIN = "admin"
    WAREHOUSE = "warehouse"
    QA = "qa"
    DOCS = "docs"
    CUSTOMER = "customer"


# ── Order Status ──────────────────────────────────────────────────────────────

class OrderStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ── Milestone Stages (in sequence) ────────────────────────────────────────────

class MilestoneStage(str, Enum):
    PROCUREMENT = "procurement"
    QA_VERIFICATION = "qa_verification"
    PACKAGING = "packaging"
    DOCUMENTATION = "documentation"
    CONTAINER_LOADING = "container_loading"
    SHIPMENT_DISPATCH = "shipment_dispatch"
    DELIVERED = "delivered"


class MilestoneStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


# ── Media / Upload Categories ─────────────────────────────────────────────────

class MediaCategory(str, Enum):
    PROCUREMENT = "procurement"
    QA = "qa"
    PACKAGING = "packaging"
    LOADING = "loading"


# ── Document Types ────────────────────────────────────────────────────────────

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


# ── Notification Types ────────────────────────────────────────────────────────

class NotificationType(str, Enum):
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"
    SMS = "SMS"
    ORDER = "order"
    DOCUMENT = "document"
    SHIPMENT = "shipment"
    SYSTEM = "system"
    QA = "qa"
    PAYMENT = "payment"


class NotificationChannel(str, Enum):
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"
    SMS = "SMS"


# ── Document Checklist Requirements Matrix ────────────────────────────────────

DOCUMENT_REQUIREMENTS = {
    DocumentType.invoice: True,
    DocumentType.purchase_order: True,
    DocumentType.packing_list: True,
    DocumentType.certificate_of_analysis: True,
    DocumentType.product_specification: True,
    DocumentType.bill_of_lading: False,
    DocumentType.lab_report: False,
    DocumentType.phytosanitary_certificate: False,
    DocumentType.insurance_certificate: False,
    DocumentType.certificate_of_origin: False,
    DocumentType.other: False
}



# ── Audit Actions ─────────────────────────────────────────────────────────────

class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    UPLOAD = "upload"


# ── Allowed File Types ────────────────────────────────────────────────────────

ALLOWED_IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/heic",
}

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}

ALLOWED_DOCUMENT_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".xlsx", ".docx"}


# ── Milestone sequence (used for ordering and validation) ─────────────────────

MILESTONE_SEQUENCE = [
    MilestoneStage.PROCUREMENT,
    MilestoneStage.QA_VERIFICATION,
    MilestoneStage.PACKAGING,
    MilestoneStage.DOCUMENTATION,
    MilestoneStage.CONTAINER_LOADING,
    MilestoneStage.SHIPMENT_DISPATCH,
    MilestoneStage.DELIVERED,
]
