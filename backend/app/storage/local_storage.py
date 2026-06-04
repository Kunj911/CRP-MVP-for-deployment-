"""
app/storage/local_storage.py

Local filesystem storage backend — for development only.

Files are saved to settings.LOCAL_UPLOAD_DIR (default: ./uploads/)
and served via a static file mount on the FastAPI app.

Storage path structure:
  ./uploads/{env}/orders/{order_id}/{category}/{uuid}.{ext}

To enable static file serving in main.py (dev only):
    from fastapi.staticfiles import StaticFiles
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
"""

import logging
import os
from pathlib import Path

from app.core.exceptions import StorageException
from app.storage.base import StorageBackend
from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LocalStorage(StorageBackend):
    """
    Saves files to the local filesystem under settings.LOCAL_UPLOAD_DIR.
    Returns a URL in the form: {BACKEND_URL}/uploads/{path}
    """

    def __init__(self):
        self.base_dir = Path(settings.LOCAL_UPLOAD_DIR).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _validate_path(self, destination_path: str) -> Path:
        """
        INPUT-003: Resolve the full path and verify it stays within base_dir.
        Prevents path traversal attacks using ../ or symlinks.
        """
        # Normalize separators and strip leading slashes
        clean_path = destination_path.replace("\\", "/").lstrip("/")
        full_path = (self.base_dir / clean_path).resolve()

        # Security check: ensure resolved path is under base_dir
        try:
            full_path.relative_to(self.base_dir)
        except ValueError:
            raise StorageException(
                f"Path traversal blocked: '{destination_path}' escapes upload directory"
            )

        return full_path

    def upload(self, file_source: bytes | str, destination_path: str, content_type: str) -> str:
        """Save bytes or copy file from local path to storage and return URL."""
        full_path = self._validate_path(destination_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if isinstance(file_source, bytes):
                full_path.write_bytes(file_source)
            else:
                import shutil
                shutil.copy2(file_source, full_path)
            logger.debug("LocalStorage: saved file to %s", full_path)
        except OSError as exc:
            raise StorageException(f"Failed to write file: {exc}") from exc

        # Return a URL relative to the static mount point
        backend_url = settings.BACKEND_URL.rstrip("/")
        return f"{backend_url}/uploads/{destination_path}"

    def delete(self, file_path: str) -> None:
        """Remove a file from disk."""
        full_path = self._validate_path(file_path)
        try:
            if full_path.exists():
                full_path.unlink()
                logger.debug("LocalStorage: deleted %s", full_path)
        except OSError as exc:
            raise StorageException(f"Failed to delete file: {exc}") from exc

    def get_url(self, file_path: str) -> str:
        self._validate_path(file_path)  # Validate even for URL generation
        backend_url = settings.BACKEND_URL.rstrip("/")
        return f"{backend_url}/uploads/{file_path}"
