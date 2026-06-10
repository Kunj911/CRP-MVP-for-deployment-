"""
app/api/v1/__init__.py

Master v1 router. Aggregates all domain routers.
Imported once in main.py and mounted at /api/v1.

To add a new domain:
    1. Create app/api/v1/your_domain.py with a router
    2. Import and include it here
"""

from fastapi import APIRouter

from .auth import router as auth_router
from .documents import router as documents_router
from .milestones import router as milestones_router
from .notifications import router as notifications_router
from .orders import router as orders_router
from .uploads import router as uploads_router
from .health import router as health_router
from .admin import router as admin_router
from .customers import router as customers_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(orders_router)
api_router.include_router(milestones_router)
api_router.include_router(uploads_router)
api_router.include_router(documents_router)
api_router.include_router(notifications_router)
api_router.include_router(health_router)
api_router.include_router(customers_router)
api_router.include_router(admin_router)
