"""
app/models/__init__.py

Imports all ORM models so that:
1. Alembic can auto-detect all tables for migration generation
2. SQLAlchemy relationship resolution works correctly at startup

CRITICAL: Every new model file MUST be imported here.

Import order respects FK dependencies:
  Customer → User → Order → (everything else)
"""

from app.models.customer import Customer          # no FK deps
from app.models.user import User                  # FK → Customer
from app.models.order import Order                # FK → Customer, User
from app.models.milestone import Milestone        # FK → Order, User
from app.models.media_file import MediaFile       # FK → Order, Milestone, User
from app.models.document import Document          # FK → Order, User
from app.models.notification import Notification  # FK → Order, User
from app.models.order_document_requirement import OrderDocumentRequirement # FK → Order, Document, User
from app.models.order_event import OrderEvent         # FK → Order
from app.models.order_product import OrderProduct     # FK → Order
from app.models.audit_log import AuditLog         # FK → Order, User
from app.models.login_session import LoginSession # FK → User

# Import event listeners last so they bind to the models
import app.models.events

__all__ = [
    "Customer",
    "User",
    "Order",
    "Milestone",
    "MediaFile",
    "Document",
    "Notification",
    "OrderDocumentRequirement",
    "OrderEvent",
    "OrderProduct",
    "AuditLog",
    "LoginSession",
]


