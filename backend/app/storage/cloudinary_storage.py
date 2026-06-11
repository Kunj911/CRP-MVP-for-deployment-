"""app/storage/cloudinary_storage.py

Cloudinary storage backend.

Handles image optimization (auto-format, auto-quality) and raw file storage.
Requires: CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET in env.
"""

import logging
import mimetypes
import os

import cloudinary
import cloudinary.api
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

from app.config.settings import get_settings
from app.core.exceptions import StorageException
from app.storage.base import StorageBackend

logger = logging.getLogger(__name__)
settings = get_settings()


_IMAGE_MIMES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/bmp",
    "image/tiff",
    "image/avif",
}


def _resource_type(content_type: str) -> str:
    """Return 'image' for images, 'raw' for everything else (PDFs, docs, etc)."""
    return "image" if content_type in _IMAGE_MIMES else "raw"


def _public_id(destination_path: str) -> str:
    """Convert storage path to Cloudinary public_id (strip extension)."""
    return os.path.splitext(destination_path)[0]


class CloudinaryStorage(StorageBackend):
    """Upload, serve, and delete files via Cloudinary CDN."""

    def __init__(self):
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )

    def upload(self, file_source: bytes | str, destination_path: str, content_type: str) -> str:
        """Upload to Cloudinary and return the CDN URL."""
        resource_type = _resource_type(content_type)
        public_id = _public_id(destination_path)

        upload_kwargs = {
            "public_id": public_id,
            "resource_type": resource_type,
            "overwrite": True,
        }

        if resource_type == "image":
            upload_kwargs.update({
                "format": "auto",
                "quality": "auto:best",
                "fetch_format": "auto",
            })

        try:
            if isinstance(file_source, bytes):
                result = cloudinary.uploader.upload(file_source, **upload_kwargs)
            else:
                with open(file_source, "rb") as f:
                    result = cloudinary.uploader.upload(f, **upload_kwargs)
        except Exception as exc:
            raise StorageException(f"Cloudinary upload failed: {exc}") from exc

        url = result.get("secure_url")
        if not url:
            raise StorageException("Cloudinary returned no URL")
        logger.info("Cloudinary: uploaded %s -> %s", public_id, url)
        return url

    def delete(self, file_path: str) -> None:
        """Delete a file from Cloudinary by its storage path."""
        resource_type = _resource_type(
            mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        )
        public_id = _public_id(file_path)
        try:
            result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
            if result.get("result") == "ok" or result.get("result") == "not found":
                logger.debug("Cloudinary: deleted %s (%s)", public_id, result["result"])
            else:
                logger.warning("Cloudinary: delete returned %s for %s", result, public_id)
        except Exception as exc:
            raise StorageException(f"Cloudinary delete failed: {exc}") from exc

    def get_url(self, file_path: str) -> str:
        """Return the CDN URL for a stored file without fetching from Cloudinary."""
        public_id = _public_id(file_path)
        resource_type = _resource_type(
            mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        )
        url, _ = cloudinary_url(public_id, resource_type=resource_type, secure=True)
        return url
