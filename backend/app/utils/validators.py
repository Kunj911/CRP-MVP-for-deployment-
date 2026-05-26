"""
app/utils/validators.py

File upload validators — run before any file is stored.

Checks:
  - File size against configured limits
  - MIME type against allowed sets
  - File extension against allowed sets
  - Basic magic byte check for images (prevents fake extensions)

Used by upload_service.py before calling storage.upload().
"""

import logging
from typing import Optional

from fastapi import UploadFile

from app.core.exceptions import FileTooLargeException, InvalidFileTypeException
from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Allowed types (match constants.py) ───────────────────────────────────────

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
ALLOWED_IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}

ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".xlsx", ".docx"}
ALLOWED_DOCUMENT_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

# ── Magic bytes (first bytes of file) ────────────────────────────────────────
# Used to detect actual file format regardless of declared content-type.

_IMAGE_MAGIC_BYTES: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff", "JPEG"),
    (b"\x89PNG\r\n\x1a\n", "PNG"),
    (b"RIFF", "WEBP"),       # WebP starts with RIFF....WEBP
    (b"\x00\x00\x00", "HEIC"),  # simplified — HEIC container
]

_PDF_MAGIC = b"%PDF"


def _get_extension(filename: str) -> str:
    """Return lowercase file extension including dot, e.g. '.jpg'"""
    parts = filename.rsplit(".", 1)
    if len(parts) < 2:
        return ""
    return f".{parts[1].lower()}"


def _check_image_magic(header: bytes) -> bool:
    """Return True if the file header looks like a known image format."""
    for magic, _ in _IMAGE_MAGIC_BYTES:
        if header.startswith(magic):
            # WebP needs additional check: RIFF....WEBP
            if magic == b"RIFF":
                return len(header) >= 12 and header[8:12] == b"WEBP"
            return True
    # HEIC/HEIF: ISO Base Media File Format — look for 'ftyp' box
    # The 'ftyp' marker appears at bytes 4-8 in the file header
    if len(header) >= 12 and header[4:8] == b"ftyp":
        # Verify it's a HEIF brand (heic, heix, mif1, etc.)
        brand = header[8:12]
        heif_brands = {b"heic", b"heix", b"mif1", b"msf1", b"hevc", b"hevx"}
        if brand in heif_brands:
            return True
    return False  # Unknown format — reject


# ── Public validators ─────────────────────────────────────────────────────────

def validate_image_file(filename: str, content_type: str, file_size: int, header: bytes) -> None:
    """
    Validate an uploaded image file without holding the full file in RAM.

    Checks:
      1. File size ≤ settings.MAX_PHOTO_SIZE_BYTES
      2. Content-type in ALLOWED_IMAGE_MIME_TYPES
      3. Extension in ALLOWED_IMAGE_EXTENSIONS
      4. Magic bytes confirm it is actually an image

    Raises FileTooLargeException or InvalidFileTypeException on failure.
    """
    # 1. Size check
    if file_size > settings.MAX_PHOTO_SIZE_BYTES:
        raise FileTooLargeException(max_mb=settings.MAX_PHOTO_SIZE_MB)

    # 2. MIME type check
    content_type = (content_type or "").lower()
    if content_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise InvalidFileTypeException(allowed=ALLOWED_IMAGE_EXTENSIONS)

    # 3. Extension check
    ext = _get_extension(filename)
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise InvalidFileTypeException(allowed=ALLOWED_IMAGE_EXTENSIONS)

    # 4. Magic bytes check (first 16 bytes)
    if not _check_image_magic(header[:16]):
        raise InvalidFileTypeException(
            allowed=ALLOWED_IMAGE_EXTENSIONS
        )

    logger.debug(
        "Image validation passed: name=%s size=%d bytes type=%s",
        filename, file_size, content_type,
    )


def validate_document_file(filename: str, content_type: str, file_size: int, header: bytes) -> None:
    """
    Validate an uploaded document file (PDF, XLSX, DOCX) without holding the full file in RAM.

    Checks:
      1. File size ≤ settings.MAX_DOCUMENT_SIZE_BYTES
      2. Content-type in ALLOWED_DOCUMENT_MIME_TYPES
      3. Extension in ALLOWED_DOCUMENT_EXTENSIONS
      4. Magic bytes confirm PDF (for .pdf files)

    Raises FileTooLargeException or InvalidFileTypeException on failure.
    """
    # 1. Size check
    if file_size > settings.MAX_DOCUMENT_SIZE_BYTES:
        raise FileTooLargeException(max_mb=settings.MAX_DOCUMENT_SIZE_MB)

    # 2. MIME type check
    content_type = (content_type or "").lower()
    if content_type not in ALLOWED_DOCUMENT_MIME_TYPES:
        raise InvalidFileTypeException(allowed=ALLOWED_DOCUMENT_EXTENSIONS)

    # 3. Extension check
    ext = _get_extension(filename)
    if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise InvalidFileTypeException(allowed=ALLOWED_DOCUMENT_EXTENSIONS)

    # 4. PDF magic byte check
    if ext == ".pdf":
        if not header[:4] == _PDF_MAGIC:
            raise InvalidFileTypeException(
                allowed={".pdf"}
            )

    logger.debug(
        "Document validation passed: name=%s size=%d bytes type=%s",
        filename, file_size, content_type,
    )

