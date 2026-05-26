"""
app/utils/image_processor.py

Image compression and processing utilities using Pillow.

Responsibilities:
  - Compress images that exceed the compression threshold
  - Strip EXIF metadata (privacy + size reduction)
  - Convert HEIC to JPEG for broad compatibility
  - Generate consistent output format (JPEG for photos)
  - Maintain aspect ratio during resize

Used by upload_service.py AFTER validation, BEFORE storage.upload().

Dependencies:
    pip install Pillow pillow-heif
"""

import io
import logging
from typing import Optional

from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

# Compress if image exceeds this size (bytes) — 2MB
COMPRESSION_THRESHOLD_BYTES = 2 * 1024 * 1024

# Max dimension (width or height) after resize
MAX_DIMENSION_PX = 2048

# JPEG output quality (1–95). 85 gives good quality at ~60% size reduction.
JPEG_QUALITY = 85

# Output format for all processed images
OUTPUT_FORMAT = "JPEG"
OUTPUT_CONTENT_TYPE = "image/jpeg"
OUTPUT_EXTENSION = ".jpg"


def process_image(
    input_file_path: str,
    original_filename: str,
    force_compress: bool = False,
) -> tuple[bytes, str, str]:
    """
    Process an uploaded image:
      1. Detect if HEIC — convert to JPEG
      2. Strip EXIF metadata
      3. Resize if largest dimension > MAX_DIMENSION_PX
      4. Compress if size > COMPRESSION_THRESHOLD_BYTES or force_compress=True

    Args:
        input_file_path:   Absolute path to the local temporary file
        original_filename: Original filename (used to detect HEIC)
        force_compress:    Always compress regardless of size

    Returns:
        Tuple of (processed_bytes, content_type, new_extension)
        e.g. (bytes, "image/jpeg", ".jpg")
    """
    import os
    is_heic = original_filename.lower().endswith((".heic", ".heif"))

    if is_heic:
        with open(input_file_path, "rb") as f:
            file_bytes = f.read()
        file_bytes = _convert_heic_to_jpeg(file_bytes)
        original_size = len(file_bytes)
    else:
        original_size = os.path.getsize(input_file_path)

    needs_processing = force_compress or original_size > COMPRESSION_THRESHOLD_BYTES

    if not needs_processing and not is_heic:
        logger.debug(
            "Image skipped compression (size=%d bytes, threshold=%d bytes)",
            original_size, COMPRESSION_THRESHOLD_BYTES,
        )
        ext = _get_ext(original_filename)
        mime = _ext_to_mime(ext)
        with open(input_file_path, "rb") as f:
            return f.read(), mime, ext

    try:
        if is_heic:
            img = Image.open(io.BytesIO(file_bytes))
        else:
            img = Image.open(input_file_path)

        # Fix orientation from EXIF before stripping
        img = ImageOps.exif_transpose(img)

        # Strip all EXIF data (privacy + size)
        img_no_exif = Image.new(img.mode, img.size)
        img_no_exif.putdata(list(img.getdata()))
        img = img_no_exif

        # Convert to RGB (handles RGBA PNG, palette mode, etc.)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # Resize if too large
        w, h = img.size
        if w > MAX_DIMENSION_PX or h > MAX_DIMENSION_PX:
            img.thumbnail((MAX_DIMENSION_PX, MAX_DIMENSION_PX), Image.LANCZOS)
            logger.debug(
                "Image resized: %dx%d → %dx%d",
                w, h, img.width, img.height,
            )

        # Compress to JPEG
        output = io.BytesIO()
        img.save(output, format=OUTPUT_FORMAT, quality=JPEG_QUALITY, optimize=True)
        processed_bytes = output.getvalue()

        reduction = round((1 - len(processed_bytes) / original_size) * 100, 1)
        logger.info(
            "Image processed: %s → %d bytes (%.1f%% reduction)",
            original_filename, len(processed_bytes), reduction,
        )

        return processed_bytes, OUTPUT_CONTENT_TYPE, OUTPUT_EXTENSION

    except Exception as exc:
        # If processing fails, return original bytes unmodified
        logger.warning(
            "Image processing failed for '%s': %s — using original",
            original_filename, exc,
        )
        ext = _get_ext(original_filename)
        with open(input_file_path, "rb") as f:
            return f.read(), _ext_to_mime(ext), ext


def _convert_heic_to_jpeg(heic_bytes: bytes) -> bytes:
    """
    Convert HEIC/HEIF bytes to JPEG using pillow-heif.
    Falls back gracefully if pillow-heif is not installed.
    """
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
        img = Image.open(io.BytesIO(heic_bytes))
        img = img.convert("RGB")
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=JPEG_QUALITY)
        logger.debug("HEIC converted to JPEG successfully")
        return output.getvalue()
    except ImportError:
        logger.warning(
            "pillow-heif not installed — HEIC file will be stored as-is. "
            "Run: pip install pillow-heif"
        )
        return heic_bytes
    except Exception as exc:
        logger.warning("HEIC conversion failed: %s — using original bytes", exc)
        return heic_bytes


def _get_ext(filename: str) -> str:
    """Return lowercase extension with dot, e.g. '.jpg'"""
    parts = filename.rsplit(".", 1)
    return f".{parts[1].lower()}" if len(parts) == 2 else ".jpg"


def _ext_to_mime(ext: str) -> str:
    _map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".heic": "image/heic",
        ".heif": "image/heif",
    }
    return _map.get(ext.lower(), "image/jpeg")
