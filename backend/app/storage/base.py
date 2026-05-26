"""
app/storage/base.py

Abstract storage backend interface.

All storage implementations (local, S3, Cloudinary) must implement this.
The upload service imports this interface — never a concrete implementation directly.
This allows swapping backends via settings.STORAGE_BACKEND with zero service changes.
"""

from abc import ABC, abstractmethod


class StorageBackend(ABC):
    """
    Abstract base class for file storage.

    Implementations:
      - local_storage.LocalStorage     → ./uploads/ directory (dev)
      - s3_storage.S3Storage           → AWS S3 (production)
      - cloudinary_storage.Cloudinary  → Cloudinary (alt production)
    """

    @abstractmethod
    def upload(self, file_source: bytes | str, destination_path: str, content_type: str) -> str:
        """
        Upload file content to the given destination path.

        Args:
            file_source:      Raw bytes OR absolute path to the local source file
            destination_path: Path within the storage system
                              e.g. "production/orders/42/qa/uuid.jpg"
            content_type:     MIME type e.g. "image/jpeg", "application/pdf"

        Returns:
            Public or signed URL to the stored file
        """
        ...

    @abstractmethod
    def delete(self, file_path: str) -> None:
        """
        Delete a file from storage by its path.

        Args:
            file_path: Same path string that was passed to upload()
        """
        ...

    @abstractmethod
    def get_url(self, file_path: str) -> str:
        """
        Return the accessible URL for a stored file.

        For S3: generates a presigned URL.
        For local: returns the static file URL.
        For Cloudinary: returns the CDN URL.
        """
        ...
