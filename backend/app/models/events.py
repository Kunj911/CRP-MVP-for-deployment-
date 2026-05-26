"""
app/models/events.py

SQLAlchemy event listeners for automatic audit logging.
This ensures that core domain changes are immutably logged to the DB,
even if the service layer forgets to call _log_audit.
"""

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.milestone import Milestone
from app.models.audit_log import AuditLog
from app.models.user import User

def _get_current_user_id() -> int:
    # In a real ASGI app with request context, you'd use contextvars
    # For simplicity, fallback to a system id (e.g. 0) if no context available.
    return 0

@event.listens_for(Order, "after_update")
def receive_order_after_update(mapper, connection, target):
    """Automatically log when an order status or active stage changes."""
    state = event.inspect(target)
    
    changes = []
    if state.attrs.status.history.has_changes():
        changes.append(f"Status changed to {target.status}")
        
    if state.attrs.active_stage.history.has_changes():
        changes.append(f"Active stage changed to {target.active_stage}")
        
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
    state = event.inspect(target)
    
    if state.attrs.status.history.has_changes():
        connection.execute(
            AuditLog.__table__.insert(),
            {
                "user_id": _get_current_user_id(),
                "action_type": "UPDATE",
                "target_table": "milestones",
                "target_id": target.id,
                "order_id": target.order_id,
                "description": f"Milestone '{target.milestone_type}' status updated to {target.status}"
            }
        )
