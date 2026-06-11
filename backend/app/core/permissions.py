"""
app/core/permissions.py

DEPRECATED — This file contains dead code that is NOT used by any route handler.
Route-level access control is now enforced via `app/api/deps.py` role-typed
dependencies (CurrentUser, AdminUser, PhotoUploaderUser, etc.) and inline checks
in service-layer functions.

This file is kept for reference only and will be removed in the next major release.
"""

from typing import Callable

from app.core.exceptions import ForbiddenException
from app.utils.constants import UserRole


# ── Permission sets per role (REFERENCE ONLY — NOT ACTIVE) ────────────────────
# These are not loaded or checked anywhere in the current codebase.

ROLE_PERMISSIONS: dict[UserRole, set[str]] = {
    UserRole.SUPER_ADMIN: {
        "orders:read", "orders:write", "orders:delete",
        "milestones:read", "milestones:write",
        "uploads:photo", "uploads:document",
        "documents:read", "documents:delete",
        "qa:read", "qa:write",
        "customers:read", "customers:write",
        "notifications:read",
        "audit:read",
        "users:read", "users:write",
    },
    UserRole.ADMIN: {
        "orders:read", "orders:write", "orders:delete",
        "milestones:read", "milestones:write",
        "uploads:photo", "uploads:document",
        "documents:read", "documents:delete",
        "qa:read", "qa:write",
        "customers:read", "customers:write",
        "notifications:read",
        "audit:read",
        "users:read", "users:write",
    },
    UserRole.WAREHOUSE: {
        "orders:read",
        "milestones:read", "milestones:write",
        "uploads:photo",
        "documents:read",
        "notifications:read",
    },
    UserRole.QA: {
        "orders:read",
        "milestones:read", "milestones:write",
        "uploads:photo",
        "uploads:document",
        "documents:read",
        "qa:read", "qa:write",
        "notifications:read",
    },
    UserRole.DOCS: {
        "orders:read",
        "milestones:read",
        "uploads:document",
        "documents:read", "documents:delete",
        "notifications:read",
    },
    UserRole.CUSTOMER: {
        "orders:read_own",
        "milestones:read",
        "documents:read",
        "qa:read",
        "notifications:read",
    },
}


def has_permission(role: UserRole, permission: str) -> bool:
    """Return True if the given role has the specified permission."""
    return permission in ROLE_PERMISSIONS.get(role, set())


def check_permission(role: UserRole, permission: str) -> None:
    """Raise ForbiddenException if the role lacks the permission."""
    if not has_permission(role, permission):
        raise ForbiddenException(
            f"Role '{role}' does not have permission: '{permission}'"
        )


# ── Route-level dependency factory ────────────────────────────────────────────

def require_roles(*allowed_roles: UserRole):
    """
    FastAPI dependency factory. Restricts a route to specific roles.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_roles(UserRole.ADMIN))])
        async def admin_route():
            ...

    Or injected via get_current_user in deps.py for finer control.
    """
    allowed = set(allowed_roles)

    def _check(current_user):
        if current_user.role not in allowed:
            raise ForbiddenException(
                f"Access restricted. Required role(s): "
                f"{', '.join(r.value for r in allowed)}"
            )
        return current_user

    return _check
