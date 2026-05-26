"""
app/storage/__init__.py

Storage backend factory.

Reads settings.STORAGE_BACKEND and returns the correct implementation.
Import get_storage() wherever you need to perform file operations.

Usage:
    from app.storage import get_storage
    storage = get_storage()
    url = storage.upload(file_bytes, path, content_type)

Switching backends:
    Set STORAGE_BACKEND=local | s3 | cloudinary in .env
    No code changes required anywhere else.
"""

from functools import lru_cache

from app.storage.base import StorageBackend


@lru_cache(maxsize=1)
def get_storage() -> StorageBackend:
    """
    Return the configured storage backend (cached — instantiated once).
    """
    from app.config.settings import get_settings
    settings = get_settings()
    backend = settings.STORAGE_BACKEND.lower()

    if backend == "local":
        from app.storage.local_storage import LocalStorage
        return LocalStorage()

    elif backend == "s3":
        from app.storage.s3_storage import S3Storage
        return S3Storage()

    elif backend == "cloudinary":
        from app.storage.cloudinary_storage import CloudinaryStorage
        return CloudinaryStorage()

    else:
        raise ValueError(
            f"Unknown STORAGE_BACKEND: '{backend}'. "
            "Expected: 'local', 's3', or 'cloudinary'"
        )
