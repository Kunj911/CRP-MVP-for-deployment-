"""
app/core/exceptions.py

Custom exception classes for the Live-Trace application.

Raise these in service layer. The global exception handler in
main.py converts them into the standard API error envelope:
  { "success": false, "error": { "code": "...", "message": "..." } }
"""

from fastapi import HTTPException, status


# ── Base ──────────────────────────────────────────────────────────────────────

class LiveTraceException(HTTPException):
    """Base exception for all application-level errors."""

    def __init__(self, status_code: int, code: str, message: str):
        self.error_code = code
        super().__init__(status_code=status_code, detail=message)


# ── Auth ──────────────────────────────────────────────────────────────────────

class UnauthorizedException(LiveTraceException):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            message=message,
        )


class ForbiddenException(LiveTraceException):
    def __init__(self, message: str = "You do not have permission to perform this action"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            message=message,
        )


class InvalidCredentialsException(LiveTraceException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="INVALID_CREDENTIALS",
            message="Invalid email or password",
        )


class TokenExpiredException(LiveTraceException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="TOKEN_EXPIRED",
            message="Your session has expired. Please log in again",
        )


class AccountLockedException(LiveTraceException):
    """Raised when brute-force lockout is active for an account or IP."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="ACCOUNT_LOCKED",
            message="Too many failed login attempts. Please try again in 15 minutes.",
        )


# ── Resource ──────────────────────────────────────────────────────────────────

class NotFoundException(LiveTraceException):
    def __init__(self, resource: str = "Resource", resource_id: str | int | None = None):
        message = f"{resource} not found"
        if resource_id is not None:
            message = f"{resource} with id '{resource_id}' not found"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=message,
        )


class ConflictException(LiveTraceException):
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            code="CONFLICT",
            message=message,
        )


# ── Validation ────────────────────────────────────────────────────────────────

class ValidationException(LiveTraceException):
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message=message,
        )


# ── Upload ────────────────────────────────────────────────────────────────────

class FileTooLargeException(LiveTraceException):
    def __init__(self, max_mb: int):
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            code="FILE_TOO_LARGE",
            message=f"File exceeds the maximum allowed size of {max_mb}MB",
        )


class InvalidFileTypeException(LiveTraceException):
    def __init__(self, allowed: set[str] | None = None):
        message = "Invalid file type"
        if allowed:
            message += f". Allowed types: {', '.join(sorted(allowed))}"
        super().__init__(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            code="INVALID_FILE_TYPE",
            message=message,
        )


class StorageException(LiveTraceException):
    def __init__(self, message: str = "File storage operation failed"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="STORAGE_ERROR",
            message=message,
        )


# ── Server ────────────────────────────────────────────────────────────────────

class ServerException(LiveTraceException):
    def __init__(self, message: str = "An unexpected error occurred"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="SERVER_ERROR",
            message=message,
        )
