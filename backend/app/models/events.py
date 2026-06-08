"""
app/models/events.py

SQLAlchemy event listeners for automatic audit logging.
This ensures that core domain changes are immutably logged to the DB,
even if the service layer forgets to call _log_audit.
"""

from typing import Optional
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.milestone import Milestone
from app.models.audit_log import AuditLog
from app.models.user import User

def _get_current_user_id() -> Optional[int]:
    # In a real ASGI app with request context, you'd use contextvars
    # For simplicity, fallback to None if no context available.
    return None

@event.listens_for(Order, "after_update")
def receive_order_after_update(mapper, connection, target):
    """Automatically log when an order status changes."""
    state = inspect(target)
    
    changes = []
    if state.attrs.shipment_status.history.has_changes():
        changes.append(f"Status changed to {target.shipment_status}")
        
    if changes:
        description = " | ".join(changes)
        connection.execute(
            AuditLog.__table__.insert(),
            {
                "user_id": _get_current_user_id(),
                "action_type": "UPDATE",
                "target_table": "orders",
                "target_id": target.id,
                "order_id": target.id,
                "description": description
            }
        )

@event.listens_for(Milestone, "after_update")
def receive_milestone_after_update(mapper, connection, target):
    """Automatically log milestone updates."""
    state = inspect(target)
    
    if state.attrs.status.history.has_changes():
        connection.execute(
            AuditLog.__table__.insert(),
            {
                "user_id": _get_current_user_id(),
                "action_type": "UPDATE",
                "target_table": "milestones",
                "target_id": target.id,
                "order_id": target.order_id,
                "description": f"Milestone '{target.stage_name}' status updated to {target.status}"
            }
        )

