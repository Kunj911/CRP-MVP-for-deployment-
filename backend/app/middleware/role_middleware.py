"""
app/middleware/role_middleware.py

Role-check decorator factory for route-level RBAC enforcement.

IMPORTANT: For standard FastAPI routes, use the Annotated dependencies
from app/api/deps.py (AdminUser, StaffUser, etc.) — they are cleaner,
testable, and show correctly in OpenAPI docs.

Use this module when you need:
  - A reusable decorator for class-based views
  - RBAC logic outside the FastAPI dependency system
  - Custom permission checks beyond simple role matching

Usage example (decorator style):
    from app.middleware.role_middleware import roles_required

    @router.get("/admin-resource")
    @roles_required("ADMIN", "SUPER_ADMIN")
    def admin_resource(current_user: CurrentUser):
        ...

Usage example (inline check):
    from app.middleware.role_middleware import check_role

    def my_service_func(user: User):
        check_role(user, allowed={"ADMIN", "QA"})
        ...
"""

import functools
import logging
from typing import Set

from app.core.exceptions import ForbiddenException
from app.models.user import User

logger = logging.getLogger(__name__)

# ── Grouped role sets (single source of truth) ────────────────────────────────

ROLE_GROUPS = {
    "super_admin":  {"SUPER_ADMIN"},
    "admin":        {"SUPER_ADMIN", "ADMIN"},
    "staff":        {"SUPER_ADMIN", "ADMIN", "WAREHOUSE", "QA", "DOCUMENTATION"},
    "warehouse":    {"SUPER_ADMIN", "ADMIN", "WAREHOUSE"},
    "qa":           {"SUPER_ADMIN", "ADMIN", "QA"},
    "docs":         {"SUPER_ADMIN", "ADMIN", "DOCUMENTATION"},
    "customer":     {"CUSTOMER"},
}


# ── Inline check (for service layer) ─────────────────────────────────────────

def check_role(user: User, allowed: Set[str]) -> None:
    """
    Raise ForbiddenException if user.role is not in allowed.

    Use in service layer when role enforcement depends on runtime data
    (e.g., a customer can only see THEIR OWN orders — not all orders).
    """
    if user.role not in allowed:
        raise ForbiddenException(
            f"Access denied. Your role '{user.role}' is not permitted for this action."
        )


def check_role_group(user: User, group: str) -> None:
    """
    Check against a named ROLE_GROUPS entry.

    Example:
        check_role_group(user, "qa")  →  allowed if SUPER_ADMIN, ADMIN, or QA
    """
    allowed = ROLE_GROUPS.get(group)
    if allowed is None:
        raise ValueError(f"Unknown role group: '{group}'")
    check_role(user, allowed)


# ── Decorator (for FastAPI route functions) ───────────────────────────────────

def roles_required(*allowed_roles: str):
    """
    Decorator that enforces role-based access on a route function.

    The route function MUST have a parameter named `current_user`
    (injected via FastAPI dependency).

    Example:
        @router.delete("/orders/{id}")
        @roles_required("ADMIN", "SUPER_ADMIN")
        def delete_order(order_id: int, current_user: CurrentUser, db: DbSession):
            ...
    """
    allowed = set(allowed_roles)

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            user: User = kwargs.get("current_user")
            if user is None:
                raise ForbiddenException("No authenticated user in request context")
            check_role(user, allowed)
            return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            user: User = kwargs.get("current_user")
            if user is None:
                raise ForbiddenException("No authenticated user in request context")
            check_role(user, allowed)
            return func(*args, **kwargs)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
