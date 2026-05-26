"""
app/services/document_vault_service.py

Business logic for the Document Vault.
Handles secure document downloads, access validation, and audit logging.
"""

import logging
from typing import Tuple, Optional
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.exceptions import (
    ForbiddenException,
    NotFoundException,
)
from app.models.audit_log import AuditLog
from app.models.document import Document
from app.models.order import Order
from app.models.user import User
from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


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


def get_document_for_download(
    doc_id: int,
    current_user: User,
    db: Session,
    ip_address: str | None = None,
) -> Tuple[Document, str, bool]:
    """
    Validates access and prepares a document for secure download.
    
    Returns:
        (Document, path_or_url, is_local_file)
        
        - If the storage is local, returns the physical file path and True.
        - If the storage is cloud (S3/Cloudinary), returns the URL and False.
    """
    # 1. Fetch document and related order
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise NotFoundException("Document", doc_id)

    order = db.query(Order).filter(Order.id == doc.order_id).first()
    if not order:
        raise NotFoundException("Order", doc.order_id)

    # 2. Access Control: Customers can only download docs for their own orders.
    # Staff (ADMIN, WAREHOUSE, QA, DOCS) can download any document.
    if current_user.role == "CUSTOMER":
        if order.customer_id != current_user.customer_id:
            logger.warning(
                "Unauthorized download attempt: user_id=%s doc_id=%s ip=%s",
                current_user.id, doc_id, ip_address or "unknown"
            )
            raise ForbiddenException("You do not have permission to download this document.")

    # 3. DATA-002: Enhanced audit logging with IP and context
    _log_audit(
        db=db,
        user_id=current_user.id,
        action_type="DOWNLOAD",
        target_table="documents",
        target_id=doc.id,
        order_id=order.id,
        description=(
            f"User downloaded document: {doc.document_type} ('{doc.file_name}') "
            f"| order_id={order.id} customer_id={order.customer_id} "
            f"| ip={ip_address or 'unknown'}"
        ),
    )
    db.commit()

    logger.info(
        "Document downloaded: doc_id=%s by user_id=%s ip=%s",
        doc.id, current_user.id, ip_address or "unknown",
    )

    # 4. Determine how to serve the file
    # For local storage in development, the URL looks like: http://localhost:8000/uploads/...
    # We want to serve it securely via FileResponse instead of exposing static paths.
    backend = settings.STORAGE_BACKEND.lower()
    
    if backend == "local":
        # Extract the relative path from the URL
        # e.g., http://localhost:8000/uploads/development/orders/1/...
        if "/uploads/" in doc.file_url:
            relative_path = doc.file_url.split("/uploads/", 1)[-1]
            base_dir = Path(settings.LOCAL_UPLOAD_DIR).resolve()
            physical_path = (base_dir / relative_path).resolve()
            
            # INPUT-003: Path traversal protection — ensure path stays within base_dir
            try:
                physical_path.relative_to(base_dir)
            except ValueError:
                logger.error(
                    "Path traversal blocked for doc_id=%s: resolved path '%s' "
                    "escapes base_dir '%s'",
                    doc.id, physical_path, base_dir,
                )
                raise ForbiddenException("Invalid file path detected.")
            
            if not physical_path.exists():
                logger.error("Physical file missing for doc_id=%s at %s", doc.id, physical_path)
                raise NotFoundException("Physical file", doc.id)
                
            return doc, str(physical_path), True
            
    elif backend == "s3":
        import boto3
        from urllib.parse import urlparse
        
        parsed_url = urlparse(doc.file_url)
        key = parsed_url.path.lstrip('/')
        
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION,
        )
        
        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.AWS_S3_BUCKET, "Key": key},
            ExpiresIn=60,
        )
        return doc, presigned_url, False
    
    # Fallback for Cloudinary or unknown backends
    return doc, doc.file_url, False
