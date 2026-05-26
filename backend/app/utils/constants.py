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
    INVOICE = "invoice"
    BL_COPY = "bl_copy"
    CERTIFICATE = "certificate"
    LAB_REPORT = "lab_report"
    PACKING_LIST = "packing_list"
    COA = "coa"
    OTHER = "other"


# ── Notification Types ────────────────────────────────────────────────────────

class NotificationType(str, Enum):
    MILESTONE_COMPLETED = "milestone_completed"
    DOCUMENT_UPLOADED = "document_uploaded"
    ORDER_CREATED = "order_created"
    ORDER_DISPATCHED = "order_dispatched"


class NotificationChannel(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"


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
