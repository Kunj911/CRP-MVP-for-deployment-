"""
app/api/deps.py

Shared FastAPI dependencies — UPDATED with real User model lookup.

Replaces the _UserStub placeholder from the initial wiring phase.
All route handlers import their auth dependencies from here.

Available dependencies:
  - DbSession          → yields a SQLAlchemy Session
  - CurrentUser        → authenticated User (any role)
  - AdminUser          → authenticated User, role = ADMIN or SUPER_ADMIN
  - SuperAdminUser     → authenticated User, role = SUPER_ADMIN only
  - StaffUser          → authenticated User, any internal role (not CUSTOMER)
  - WarehouseUser      → ADMIN, SUPER_ADMIN, or WAREHOUSE
  - QAUser             → ADMIN, SUPER_ADMIN, or QA
  - DocsUser           → ADMIN, SUPER_ADMIN, or DOCUMENTATION
  - CustomerUser       → CUSTOMER role only

Usage in a route:
    @router.get("/me")
    def get_me(current_user: CurrentUser):
        return current_user

SECURITY NOTE (LOGIC-002 — Privilege Escalation Prevention):
    If/when user-creation or role-modification endpoints are added:
    1. ONLY SUPER_ADMIN may assign or change roles.
    2. A user MUST NOT be able to self-assign SUPER_ADMIN.
    3. Role changes MUST be audit-logged with the assigner's identity.
    4. Role changes to SUPER_ADMIN should require additional verification.
"""

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_access_token
from app.database.connection import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

# ── DB session ────────────────────────────────────────────────────────────────

DbSession = Annotated[Session, Depends(get_db)]


# ── Core auth dependency ──────────────────────────────────────────────────────

def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Extract and validate JWT from the Authorization: Bearer <token> header.
    Performs a real DB lookup — returns a live User ORM object.

    Raises:
      UnauthorizedException — missing token, invalid token, or inactive user
    """
    if not credentials:
        raise UnauthorizedException("No authentication token provided")

    payload = decode_access_token(credentials.credentials)
    user_id_str = payload.get("sub")
    
    # Store token metadata for revocation during logout
    request.state.jti = payload.get("jti")
    request.state.exp = payload.get("exp")

    if not user_id_str:
        raise UnauthorizedException("Malformed token: missing subject")

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise UnauthorizedException("Malformed token: invalid subject")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise UnauthorizedException("User not found")

    if not user.is_active:
        raise UnauthorizedException("Your account has been deactivated")

    return user


# ── Role-scoped dependencies ──────────────────────────────────────────────────

_SUPER_ADMIN = {"SUPER_ADMIN"}
_ADMIN_AND_ABOVE = {"SUPER_ADMIN", "ADMIN"}
_STAFF_ROLES = {"SUPER_ADMIN", "ADMIN", "WAREHOUSE", "QA", "DOCUMENTATION"}
_WAREHOUSE_ROLES = {"SUPER_ADMIN", "ADMIN", "WAREHOUSE"}
_QA_ROLES = {"SUPER_ADMIN", "ADMIN", "QA"}
_DOCS_ROLES = {"SUPER_ADMIN", "ADMIN", "DOCUMENTATION"}
_PHOTO_UPLOAD_ROLES = {"SUPER_ADMIN", "ADMIN", "WAREHOUSE", "QA"}
_DOC_UPLOAD_ROLES = {"SUPER_ADMIN", "ADMIN", "DOCUMENTATION", "QA"}
_DOC_DELETE_ROLES = {"SUPER_ADMIN", "ADMIN", "DOCUMENTATION"}
_MEDIA_DELETE_ROLES = {"SUPER_ADMIN", "ADMIN"}
_CUSTOMER_ROLES = {"CUSTOMER"}


def _role_guard(allowed: set[str]):
    """Factory: returns a FastAPI dependency that enforces allowed roles."""
    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise ForbiddenException(
                f"Access denied. Required role(s): {', '.join(sorted(allowed))}"
            )
        return current_user
    return _check


def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """SUPER_ADMIN only."""
    if current_user.role not in _SUPER_ADMIN:
        raise ForbiddenException("Super admin access required")
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """SUPER_ADMIN or ADMIN."""
    if current_user.role not in _ADMIN_AND_ABOVE:
        raise ForbiddenException("Admin access required")
    return current_user


def require_staff(current_user: User = Depends(get_current_user)) -> User:
    """Any internal role — excludes CUSTOMER."""
    if current_user.role not in _STAFF_ROLES:
        raise ForbiddenException("Staff access required")
    return current_user


def require_warehouse(current_user: User = Depends(get_current_user)) -> User:
    """ADMIN or WAREHOUSE (can upload photos, update milestones)."""
    if current_user.role not in _WAREHOUSE_ROLES:
        raise ForbiddenException("Warehouse access required")
    return current_user


def require_qa(current_user: User = Depends(get_current_user)) -> User:
    """ADMIN or QA."""
    if current_user.role not in _QA_ROLES:
        raise ForbiddenException("QA access required")
    return current_user


def require_docs(current_user: User = Depends(get_current_user)) -> User:
    """ADMIN or DOCUMENTATION."""
    if current_user.role not in _DOCS_ROLES:
        raise ForbiddenException("Documentation team access required")
    return current_user


def require_media_deleter(current_user: User = Depends(get_current_user)) -> User:
    """ADMIN or SUPER_ADMIN (can delete media files)."""
    if current_user.role not in _MEDIA_DELETE_ROLES:
        raise ForbiddenException("Media deletion requires ADMIN or SUPER_ADMIN role")
    return current_user


def require_doc_deleter(current_user: User = Depends(get_current_user)) -> User:
    """ADMIN, SUPER_ADMIN, or DOCUMENTATION (can delete documents)."""
    if current_user.role not in _DOC_DELETE_ROLES:
        raise ForbiddenException("Document deletion requires ADMIN, SUPER_ADMIN, or DOCUMENTATION role")
    return current_user


def require_photo_uploader(current_user: User = Depends(get_current_user)) -> User:
    """ADMIN, WAREHOUSE, or QA (can upload photos)."""
    if current_user.role not in _PHOTO_UPLOAD_ROLES:
        raise ForbiddenException("Photo upload requires ADMIN, WAREHOUSE, or QA role")
    return current_user


def require_doc_uploader(current_user: User = Depends(get_current_user)) -> User:
    """ADMIN, DOCUMENTATION, or QA (can upload documents)."""
    if current_user.role not in _DOC_UPLOAD_ROLES:
        raise ForbiddenException("Document upload requires ADMIN, DOCUMENTATION, or QA role")
    return current_user


def require_customer(current_user: User = Depends(get_current_user)) -> User:
    """CUSTOMER role only — for customer-facing read endpoints."""
    if current_user.role not in _CUSTOMER_ROLES:
        raise ForbiddenException("Customer access required")
    return current_user


# ── Annotated type aliases ────────────────────────────────────────────────────
# Use these in route signatures for clean, readable injection.

CurrentUser = Annotated[User, Depends(get_current_user)]
SuperAdminUser = Annotated[User, Depends(require_super_admin)]
AdminUser = Annotated[User, Depends(require_admin)]
StaffUser = Annotated[User, Depends(require_staff)]
WarehouseUser = Annotated[User, Depends(require_warehouse)]
QAUser = Annotated[User, Depends(require_qa)]
DocsUser = Annotated[User, Depends(require_docs)]
PhotoUploaderUser = Annotated[User, Depends(require_photo_uploader)]
DocUploaderUser = Annotated[User, Depends(require_doc_uploader)]
MediaDeleterUser = Annotated[User, Depends(require_media_deleter)]
DocDeleterUser = Annotated[User, Depends(require_doc_deleter)]
CustomerUser = Annotated[User, Depends(require_customer)]
