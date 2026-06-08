"""
app/services/upload_service.py

Upload business logic for photos and documents.

Upload pipeline for PHOTOS:
  1. Stream file to temp file with size validation (chunked — never full RAM)
  2. Validate (MIME via python-magic, extension, magic bytes)
  3. Scan for malware via ClamAV
  4. Enforce customer storage quota limit
  5. Process image (compress, strip EXIF, resize if needed)
  6. Generate secure storage path
  7. Upload to storage backend (local / S3 / Cloudinary)
  8. Save MediaFile record with size + storage_key to DB
  9. Write AuditLog
  10. Clean up temp file
  11. Return MediaFileResponse

Upload pipeline for DOCUMENTS:
  1. Stream file to temp file with size validation
  2. Validate (MIME, extension, PDF magic bytes)
  3. Scan for malware via ClamAV
  4. Enforce customer storage quota limit
  5. Generate secure storage path
  6. Upload to storage backend (via temp file path — zero memory)
  7. Save Document record with size + storage_key to DB
  8. Write AuditLog
  9. Clean up temp file
  10. Return DocumentResponse
"""

import logging
import os
import tempfile
import uuid
import magic
from typing import List, Optional

from fastapi import UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.exceptions import (
    FileTooLargeException,
    ForbiddenException,
    NotFoundException,
    StorageException,
)
from app.models.audit_log import AuditLog
from app.models.document import Document
from app.models.media_file import MediaFile
from app.models.order import Order
from app.models.user import User
from app.models.order_document_requirement import OrderDocumentRequirement
from app.schemas.upload import (
    DocumentResponse,
    DocumentType,
    MediaFileResponse,
    MediaType,
    UploadSummary,
)
from app.storage import get_storage
from app.utils.image_processor import (
    COMPRESSION_THRESHOLD_BYTES,
    process_image,
)
from app.utils.validators import validate_document_file, validate_image_file
from app.utils.malware_scanner import scan_file_for_malware
from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Role rules ────────────────────────────────────────────────────────────────
_PHOTO_UPLOAD_ROLES  = {"SUPER_ADMIN", "ADMIN", "WAREHOUSE", "QA"}
_DOC_UPLOAD_ROLES    = {"SUPER_ADMIN", "ADMIN", "DOCUMENTATION"}
_DELETE_ROLES        = {"SUPER_ADMIN", "ADMIN"}

# INPUT-001: Server-side MIME → extension mapping
# Never trust the client-supplied file extension — derive it from detected MIME.
_MIME_TO_EXTENSION: dict[str, str] = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/msword": ".doc",
    "application/vnd.ms-excel": ".xls",
}

_DOCUMENT_TO_LEGACY_DB_TYPE = {
    "invoice": "INVOICE",
    "bill_of_lading": "BL_COPY",
    "certificate_of_analysis": "COA",
    "phytosanitary_certificate": "PHYTOSANITARY_CERTIFICATE",
    "lab_report": "LAB_REPORT",
    "packing_list": "PACKING_LIST",
    "other": "OTHER",
    "product_specification": "product_specification",
    "insurance_certificate": "insurance_certificate",
    "purchase_order": "purchase_order",
    "certificate_of_origin": "certificate_of_origin",
}
_LEGACY_DB_TO_DOCUMENT_TYPE = {
    legacy: current for current, legacy in _DOCUMENT_TO_LEGACY_DB_TYPE.items()
}


def _document_db_type(document_type: DocumentType | str) -> str:
    value = document_type.value if isinstance(document_type, DocumentType) else str(document_type)
    return _DOCUMENT_TO_LEGACY_DB_TYPE.get(value, "OTHER")


def _requirement_document_type(document_type: str) -> str:
    return _LEGACY_DB_TO_DOCUMENT_TYPE.get(document_type, document_type)

# Chunk size for streamed reads (64KB)
_STREAM_CHUNK_SIZE = 64 * 1024


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_order_or_404(order_id: int, db: Session) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundException("Order", order_id)
    return order


def _make_storage_path(
    order_id: int,
    category: str,
    extension: str,
) -> tuple[str, str]:
    """
    Build the storage path and generate a UUID filename.

    Returns:
        (destination_path, stored_filename)
        e.g. ("production/orders/42/qa/a1b2c3.jpg", "a1b2c3.jpg")
    """
    env = settings.APP_ENV        # development | staging | production
    file_uuid = uuid.uuid4().hex
    stored_filename = f"{file_uuid}{extension}"
    destination = f"{env}/orders/{order_id}/{category}/{stored_filename}"
    return destination, stored_filename


def _log_audit(
    db: Session,
    user_id: int,
    action_type: str,
    target_table: str,
    target_id: int,
    order_id: int,
    description: str,
) -> None:
    db.add(AuditLog(
        user_id=user_id,
        action_type=action_type,
        target_table=target_table,
        target_id=target_id,
        order_id=order_id,
        description=description,
    ))


async def _stream_to_tempfile(
    file: UploadFile,
    max_size_bytes: int,
    max_size_mb: int,
) -> tuple[tempfile._TemporaryFileWrapper, int]:
    """
    Stream upload chunks directly to a disk-based NamedTemporaryFile to avoid RAM pressure.
    Raises FileTooLargeException if limit is exceeded.
    """
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    total_size = 0
    try:
        while True:
            chunk = await file.read(_STREAM_CHUNK_SIZE)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > max_size_bytes:
                # Early abort
                raise FileTooLargeException(max_mb=max_size_mb)
            temp_file.write(chunk)
        temp_file.flush()
        temp_file.seek(0)
        return temp_file, total_size
    except Exception:
        temp_file.close()
        try:
            os.unlink(temp_file.name)
        except OSError:
            pass
        raise


def _check_customer_storage_quota(db: Session, customer_id: int, new_file_size: int) -> None:
    """
    Check if the customer has enough storage quota remaining.
    """
    from app.models.customer import Customer
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        return  # Skip if order has no customer linked (unlikely in normalized DB)

    quota_bytes = customer.storage_quota_mb * 1024 * 1024

    # Sum up existing MediaFiles size
    media_size = db.query(func.sum(MediaFile.file_size)).join(Order).filter(Order.customer_id == customer_id).scalar() or 0

    # Sum up existing Documents size
    doc_size = db.query(func.sum(Document.file_size)).join(Order).filter(Order.customer_id == customer_id).scalar() or 0

    total_used = media_size + doc_size

    if total_used + new_file_size > quota_bytes:
        raise ForbiddenException(
            f"Storage quota exceeded for customer '{customer.company_name}'. "
            f"Limit: {customer.storage_quota_mb}MB. Used: {round(total_used / (1024 * 1024), 2)}MB. "
            f"Required: {round(new_file_size / (1024 * 1024), 2)}MB."
        )


# ── Photo upload ──────────────────────────────────────────────────────────────

async def upload_photo(
    file: UploadFile,
    order_id: int,
    media_type: MediaType,
    current_user: User,
    db: Session,
    milestone_id: Optional[int] = None,
) -> UploadSummary:
    """
    Upload a procurement / packaging / QA / loading image.

    Pipeline: stream to temp → validate → scan → quota check → compress → store → DB record → audit log
    """
    if current_user.role not in _PHOTO_UPLOAD_ROLES:
        raise ForbiddenException(
            "Only ADMIN, WAREHOUSE, or QA can upload photos"
        )

    order = _get_order_or_404(order_id, db)

    # LOGIC-001: Verify order ownership for CUSTOMER role
    if current_user.role == "CUSTOMER":
        if order.customer_id != current_user.customer_id:
            raise NotFoundException("Order", order_id)

    # 1. Stream file with early size abort
    temp_file, original_size = await _stream_to_tempfile(
        file,
        max_size_bytes=settings.MAX_PHOTO_SIZE_BYTES,
        max_size_mb=settings.MAX_PHOTO_SIZE_MB,
    )

    try:
        # 2. Read first 2KB for magic check
        header_bytes = temp_file.read(2048)
        temp_file.seek(0)

        # 3. Validate MIME strictly with python-magic
        mime_type = magic.from_buffer(header_bytes, mime=True)
        allowed_mimes = {"image/jpeg", "image/png", "image/webp", "image/heic"}
        if mime_type not in allowed_mimes:
            raise ForbiddenException(f"Invalid image type. Detected: {mime_type}")

        validate_image_file(file.filename or "upload", mime_type, original_size, header_bytes)

        # 4. Enforce storage quota check
        _check_customer_storage_quota(db, order.customer_id, original_size)

        # 5. Scan for malware
        if not scan_file_for_malware(temp_file.name):
            raise ForbiddenException("Security threat detected: Malicious file detected.")

        # 6. Process (compress + EXIF strip) in threadpool to avoid blocking ASGI loop
        was_compressed = original_size > COMPRESSION_THRESHOLD_BYTES
        processed_bytes, content_type, extension = await run_in_threadpool(
            process_image,
            input_file_path=temp_file.name,
            original_filename=file.filename or "upload",
            force_compress=False,
        )

        # 7. Build storage path
        category_folder = media_type.value.lower()  # e.g. "qa_image"
        destination, stored_filename = _make_storage_path(
            order_id=order_id,
            category=category_folder,
            extension=extension,
        )

        # 8. Upload to storage backend
        storage = get_storage()
        try:
            file_url = storage.upload(
                file_source=processed_bytes,
                destination_path=destination,
                content_type=content_type,
            )
        except Exception as exc:
            raise StorageException(f"Photo upload failed: {exc}") from exc

        # 9. Save DB record
        media_record = MediaFile(
            order_id=order_id,
            milestone_id=milestone_id,
            media_type=media_type.value,
            file_name=file.filename,
            file_url=file_url,
            file_size=len(processed_bytes),
            storage_key=destination,
            uploaded_by=current_user.id,
        )
        db.add(media_record)
        db.flush()

        # 10. Audit log
        _log_audit(
            db=db,
            user_id=current_user.id,
            action_type="UPLOAD",
            target_table="media_files",
            target_id=media_record.id,
            order_id=order_id,
            description=(
                f"Photo uploaded: type={media_type.value} "
                f"file='{file.filename}' order_id={order_id}"
                + (f" milestone_id={milestone_id}" if milestone_id else "")
            ),
        )

        db.commit()
        db.refresh(media_record)
        logger.info(
            "Photo uploaded: media_id=%s order_id=%s type=%s size=%d→%d bytes",
            media_record.id, order_id, media_type.value,
            original_size, len(processed_bytes),
        )

        return UploadSummary(
            file_id=media_record.id,
            file_url=file_url,
            original_filename=file.filename or "",
            stored_filename=stored_filename,
            size_bytes=len(processed_bytes),
            was_compressed=was_compressed,
            message=f"Photo uploaded successfully as '{media_type.value}'",
        )

    finally:
        # Always cleanup temporary file from disk
        temp_file.close()
        try:
            os.unlink(temp_file.name)
        except OSError:
            pass


# ── Document upload ───────────────────────────────────────────────────────────

async def upload_document(
    file: UploadFile,
    order_id: int,
    document_type: DocumentType,
    current_user: User,
    db: Session,
) -> UploadSummary:
    """
    Upload a shipment document (Invoice, BL Copy, COA, etc.)

    Pipeline: stream to temp → validate → scan → quota check → store → DB record → audit log
    """
    if current_user.role not in _DOC_UPLOAD_ROLES:
        raise ForbiddenException(
            "Only ADMIN or DOCUMENTATION team can upload documents"
        )

    order = _get_order_or_404(order_id, db)

    # LOGIC-001: Verify order ownership for CUSTOMER role
    if current_user.role == "CUSTOMER":
        if order.customer_id != current_user.customer_id:
            raise NotFoundException("Order", order_id)

    # 1. Stream file with early size abort
    temp_file, total_size = await _stream_to_tempfile(
        file,
        max_size_bytes=settings.MAX_DOCUMENT_SIZE_BYTES,
        max_size_mb=settings.MAX_DOCUMENT_SIZE_MB,
    )

    try:
        # 2. Read first 2KB for magic check
        header_bytes = temp_file.read(2048)
        temp_file.seek(0)

        # 3. Validate MIME strictly with python-magic
        mime_type = magic.from_buffer(header_bytes, mime=True)
        allowed_doc_mimes = {
            "application/pdf", 
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/msword",
            "application/vnd.ms-excel"
        }
        if mime_type not in allowed_doc_mimes:
            raise ForbiddenException(f"Invalid document type. Detected: {mime_type}")

        validate_document_file(file.filename or "upload", mime_type, total_size, header_bytes)

        # 4. Enforce storage quota check
        _check_customer_storage_quota(db, order.customer_id, total_size)

        # 5. Scan for malware
        if not scan_file_for_malware(temp_file.name):
            raise ForbiddenException("Security threat detected: Malicious file detected.")

        # 6. Derive extension from MIME type detected by python-magic, not client filename
        ext = _MIME_TO_EXTENSION.get(mime_type)
        if not ext:
            raise ForbiddenException(
                f"Cannot determine safe file extension for MIME type: {mime_type}"
            )

        # 7. Build storage path
        destination, stored_filename = _make_storage_path(
            order_id=order_id,
            category="documents",
            extension=ext,
        )

        # 8. Upload to storage backend using temp file path (zero memory!)
        storage = get_storage()
        try:
            file_url = storage.upload(
                file_source=temp_file.name,
                destination_path=destination,
                content_type=mime_type,  # INPUT-001: Use detected MIME, not client-supplied
            )
        except Exception as exc:
            raise StorageException(f"Document upload failed: {exc}") from exc

        # 9. Save DB record
        document_db_type = _document_db_type(document_type)
        doc_record = Document(
            order_id=order_id,
            document_type=document_db_type,
            file_name=file.filename,
            file_url=file_url,
            file_size=total_size,
            storage_key=destination,
            uploaded_by=current_user.id,
            status="uploaded",
            visibility="internal",
        )
        db.add(doc_record)
        db.flush()

        # Update OrderDocumentRequirement
        req = db.query(OrderDocumentRequirement).filter(
            OrderDocumentRequirement.order_id == order_id,
            OrderDocumentRequirement.document_type == document_type.value
        ).first()
        if not req:
            req = OrderDocumentRequirement(
                order_id=order_id,
                document_type=document_type.value,
                required=False
            )
            db.add(req)
        req.uploaded = True
        req.uploaded_at = func.now()
        req.document_id = doc_record.id
        req.approved = False
        req.approved_at = None
        req.approved_by = None

        # Log OrderEvent
        from app.models.order_event import OrderEvent
        event = OrderEvent(
            order_id=order_id,
            event_type="document_uploaded",
            description=f"Document '{doc_record.file_name}' ({doc_record.document_type}) uploaded by {current_user.full_name}."
        )
        db.add(event)

        # In-app notifications to reviewers (QA, Admin)
        reviewers = db.query(User).filter(
            User.role.in_(["QA", "ADMIN", "SUPER_ADMIN"]),
            User.is_active == True
        ).all()
        for r in reviewers:
            from app.services.notification_service import create_in_app_notification
            create_in_app_notification(
                db=db,
                user_id=r.id,
                order_id=order_id,
                title="Document Review Required",
                message=f"Document '{doc_record.file_name}' ({doc_record.document_type}) has been uploaded and requires review.",
                notification_type="document",
                related_order_id=order_id,
                related_document_id=doc_record.id
            )

        # Trigger async email
        from app.tasks.document_tasks import send_document_uploaded_email
        send_document_uploaded_email.delay(order_id, doc_record.id)

        # 10. Audit log
        _log_audit(
            db=db,
            user_id=current_user.id,
            action_type="UPLOAD",
            target_table="documents",
            target_id=doc_record.id,
            order_id=order_id,
            description=(
                f"Document uploaded: type={document_type.value} "
                f"file='{file.filename}' order_id={order_id}"
            ),
        )

        db.commit()
        db.refresh(doc_record)
        logger.info(
            "Document uploaded: doc_id=%s order_id=%s type=%s size=%d bytes",
            doc_record.id, order_id, document_type.value, total_size,
        )

        return UploadSummary(
            file_id=doc_record.id,
            file_url=file_url,
            original_filename=file.filename or "",
            stored_filename=stored_filename,
            size_bytes=total_size,
            was_compressed=False,
            message=f"Document uploaded successfully as '{document_type.value}'",
        )

    finally:
        # Always cleanup temporary file from disk
        temp_file.close()
        try:
            os.unlink(temp_file.name)
        except OSError:
            pass


# ── List media for an order ───────────────────────────────────────────────────

def get_order_media(
    order_id: int,
    current_user: User,
    db: Session,
    media_type: Optional[MediaType] = None,
) -> List[MediaFileResponse]:
    """Return all media files for an order, optionally filtered by type."""
    order = _get_order_or_404(order_id, db)

    # Customer scoping
    if current_user.role == "CUSTOMER":
        if order.customer_id != current_user.customer_id:
            raise NotFoundException("Order", order_id)

    query = db.query(MediaFile).filter(MediaFile.order_id == order_id)
    if media_type:
        query = query.filter(MediaFile.media_type == media_type.value)

    files = query.order_by(MediaFile.uploaded_at.desc()).all()
    return [MediaFileResponse.model_validate(f) for f in files]


# ── List documents for an order ───────────────────────────────────────────────

def get_order_documents(
    order_id: int,
    current_user: User,
    db: Session,
    document_type: Optional[DocumentType] = None,
) -> List[DocumentResponse]:
    """Return all documents for an order, optionally filtered by type."""
    order = _get_order_or_404(order_id, db)

    # Customer scoping
    if current_user.role == "CUSTOMER":
        if order.customer_id != current_user.customer_id:
            raise NotFoundException("Order", order_id)

    query = db.query(Document).filter(
        Document.order_id == order_id,
        Document.is_deleted == False
    )
    if current_user.role == "CUSTOMER":
        query = query.filter(
            Document.status == "approved",
            Document.visibility == "customer_visible"
        )
        
    if document_type:
        query = query.filter(Document.document_type == _document_db_type(document_type))

    docs = query.order_by(Document.uploaded_at.desc()).all()
    return [DocumentResponse.model_validate(d) for d in docs]


# ── Delete media ──────────────────────────────────────────────────────────────

def delete_media_file(
    media_id: int,
    current_user: User,
    db: Session,
) -> None:
    """Delete a media file (DB record + storage). Admin only."""
    if current_user.role not in _DELETE_ROLES:
        raise ForbiddenException("Only ADMIN can delete uploaded files")

    media = db.query(MediaFile).filter(MediaFile.id == media_id).first()
    if not media:
        raise NotFoundException("MediaFile", media_id)

    # LOGIC-003: IDOR protection — verify the media belongs to an accessible order (via relationship mapping)
    order = media.order
    if current_user.role == "CUSTOMER" and order:
        if order.customer_id != current_user.customer_id:
            raise ForbiddenException("You do not have access to this file")

    # Attempt storage deletion
    storage = get_storage()
    try:
        # Use storage_key if present, fallback to parsing from URL
        path = media.storage_key
        if not path:
            path = media.file_url.split("/uploads/", 1)[-1] if "/uploads/" in media.file_url else ""
        if path:
            storage.delete(path)
    except Exception as exc:
        logger.warning("Storage delete failed for media_id=%s: %s", media_id, exc)

    _log_audit(
        db=db,
        user_id=current_user.id,
        action_type="DELETE",
        target_table="media_files",
        target_id=media_id,
        order_id=media.order_id,
        description=f"Media file deleted: media_id={media_id} file='{media.file_name}'",
    )
    db.delete(media)
    db.commit()
    logger.info("Media file deleted: media_id=%s by user_id=%s", media_id, current_user.id)


# ── Delete document ───────────────────────────────────────────────────────────

def delete_document(
    doc_id: int,
    current_user: User,
    db: Session,
) -> None:
    """Soft delete a document by marking is_deleted=True. Admin or Docs team."""
    if current_user.role not in {*_DELETE_ROLES, "DOCUMENTATION"}:
        raise ForbiddenException("Only ADMIN or DOCUMENTATION team can delete documents")

    doc = db.query(Document).filter(Document.id == doc_id, Document.is_deleted == False).first()
    if not doc:
        raise NotFoundException("Document", doc_id)

    # LOGIC-003: IDOR protection — verify document belongs to an accessible order (via relationship mapping)
    order = doc.order
    if current_user.role == "CUSTOMER" and order:
        if order.customer_id != current_user.customer_id:
            raise ForbiddenException("You do not have access to this document")

    doc.is_deleted = True

    # Update OrderDocumentRequirement
    req = db.query(OrderDocumentRequirement).filter(
        OrderDocumentRequirement.order_id == doc.order_id,
        OrderDocumentRequirement.document_id == doc.id
    ).first()
    if req:
        req.uploaded = False
        req.approved = False
        req.uploaded_at = None
        req.approved_at = None
        req.approved_by = None
        req.document_id = None

    # Log OrderEvent
    from app.models.order_event import OrderEvent
    event = OrderEvent(
        order_id=doc.order_id,
        event_type="document_deleted",
        description=f"Document '{doc.file_name}' ({doc.document_type}) deleted by {current_user.full_name}."
    )
    db.add(event)

    _log_audit(
        db=db,
        user_id=current_user.id,
        action_type="DELETE",
        target_table="documents",
        target_id=doc_id,
        order_id=doc.order_id,
        description=f"Document soft-deleted: doc_id={doc_id} type={doc.document_type} file='{doc.file_name}'",
    )
    db.commit()
    logger.info("Document soft-deleted: doc_id=%s by user_id=%s", doc_id, current_user.id)


# ── Document Checklist and Approval Workflows ─────────────────────────────────

def get_order_document_checklist(
    order_id: int,
    current_user: User,
    db: Session,
) -> List["OrderDocumentRequirement"]:
    """Retrieve checklist requirements for an order with scoping for customer visibility."""
    order = _get_order_or_404(order_id, db)
    
    # Customer scoping
    if current_user.role == "CUSTOMER":
        if order.customer_id != current_user.customer_id:
            raise NotFoundException("Order", order_id)
            
    reqs = db.query(OrderDocumentRequirement).filter(
        OrderDocumentRequirement.order_id == order_id
    ).all()
    
    # Hide document details for customers if not approved/visible
    if current_user.role == "CUSTOMER":
        for r in reqs:
            if r.document:
                if r.document.status != "approved" or r.document.visibility != "customer_visible" or r.document.is_deleted:
                    # Clear direct document linkages to hide unapproved files
                    r.document_id = None
                    r.uploaded = False
                    r.approved = False
                    r.uploaded_at = None
                    r.approved_at = None
                    
    return reqs


def approve_document(doc_id: int, current_user: User, db: Session) -> Document:
    """Approve an uploaded document, update requirement, and dispatch alerts."""
    if current_user.role not in {"QA", "ADMIN", "SUPER_ADMIN"}:
        raise ForbiddenException("Only QA or ADMIN can approve documents")
        
    doc = db.query(Document).filter(Document.id == doc_id, Document.is_deleted == False).first()
    if not doc:
        raise NotFoundException("Document", doc_id)
        
    doc.status = "approved"
    doc.visibility = "customer_visible"  # Auto-mark as customer visible on approval
    doc.reviewed_by = current_user.id
    doc.reviewed_at = func.now()
    
    # Update checklist requirement
    requirement_type = _requirement_document_type(doc.document_type)
    req = db.query(OrderDocumentRequirement).filter(
        OrderDocumentRequirement.order_id == doc.order_id,
        OrderDocumentRequirement.document_type == requirement_type
    ).first()
    
    if req:
        req.approved = True
        req.approved_at = func.now()
        req.approved_by = current_user.id
        req.uploaded = True
        req.document_id = doc.id
        
    # Log OrderEvent
    from app.models.order_event import OrderEvent
    event = OrderEvent(
        order_id=doc.order_id,
        event_type="document_approved",
        description=f"Document '{doc.file_name}' ({doc.document_type}) approved by {current_user.full_name}."
    )
    db.add(event)
    
    # In-app notification to customer contacts
    order = doc.order
    customer_users = db.query(User).filter(
        User.customer_id == order.customer_id,
        User.role == "CUSTOMER",
        User.is_active == True
    ).all()
    
    for user in customer_users:
        from app.services.notification_service import create_in_app_notification
        create_in_app_notification(
            db=db,
            user_id=user.id,
            order_id=doc.order_id,
            title="Document Approved",
            message=f"Your document '{doc.file_name}' has been approved.",
            notification_type="document",
            related_order_id=doc.order_id,
            related_document_id=doc.id
        )
        
    # Trigger Email Celery task
    from app.tasks.document_tasks import send_document_approved_email
    send_document_approved_email.delay(doc.order_id, doc.id)
    
    db.commit()
    db.refresh(doc)
    return doc


def reject_document(doc_id: int, remarks: str, current_user: User, db: Session) -> Document:
    """Reject an uploaded document, update checklist, and send alerts for revision."""
    if current_user.role not in {"QA", "ADMIN", "SUPER_ADMIN"}:
        raise ForbiddenException("Only QA or ADMIN can reject documents")
        
    doc = db.query(Document).filter(Document.id == doc_id, Document.is_deleted == False).first()
    if not doc:
        raise NotFoundException("Document", doc_id)
        
    doc.status = "rejected"
    doc.reviewed_by = current_user.id
    doc.reviewed_at = func.now()
    
    # Update checklist requirement
    requirement_type = _requirement_document_type(doc.document_type)
    req = db.query(OrderDocumentRequirement).filter(
        OrderDocumentRequirement.order_id == doc.order_id,
        OrderDocumentRequirement.document_type == requirement_type
    ).first()
    
    if req:
        req.approved = False
        req.approved_at = None
        req.approved_by = None
        
    # Log OrderEvent
    from app.models.order_event import OrderEvent
    event = OrderEvent(
        order_id=doc.order_id,
        event_type="document_rejected",
        description=f"Document '{doc.file_name}' ({doc.document_type}) rejected by {current_user.full_name}. Reason: {remarks}"
    )
    db.add(event)
    
    # In-app notification to customer contacts
    order = doc.order
    customer_users = db.query(User).filter(
        User.customer_id == order.customer_id,
        User.role == "CUSTOMER",
        User.is_active == True
    ).all()
    
    for user in customer_users:
        from app.services.notification_service import create_in_app_notification
        create_in_app_notification(
            db=db,
            user_id=user.id,
            order_id=doc.order_id,
            title="Document Rejected",
            message=f"Your document '{doc.file_name}' has been rejected. Reason: {remarks}",
            notification_type="document",
            related_order_id=doc.order_id,
            related_document_id=doc.id
        )
        
    # Trigger Email Celery task
    from app.tasks.document_tasks import send_document_rejected_email
    send_document_rejected_email.delay(doc.order_id, doc.id, remarks)
    
    db.commit()
    db.refresh(doc)
    return doc
