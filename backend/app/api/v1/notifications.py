"""
app/api/v1/notifications.py

Notification route handlers.

Endpoints:
  GET  /notifications              → list current user's notifications
  GET  /notifications?unread=true  → only PENDING/FAILED
"""

import logging
from typing import List

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import SuccessResponse
from app.schemas.notification import NotificationResponse
from app.services import notification_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Notifications"])


@router.get(
    "/notifications",
    response_model=SuccessResponse[List[NotificationResponse]],
    summary="List my notifications",
    description=(
        "Returns recent notifications for the authenticated user.\n\n"
        "- Set `?unread=true` to show only undelivered (PENDING/FAILED) notifications.\n"
        "- Sorted by creation time, newest first.\n"
        "- Limit: 50 most recent records."
    ),
)
def list_notifications(
    current_user: CurrentUser,
    db: DbSession,
    unread: bool = Query(False, description="If true, return only undelivered notifications"),
) -> SuccessResponse[List[NotificationResponse]]:
    notifications = notification_service.get_notifications_for_user(
        user_id=current_user.id,
        db=db,
        unread_only=unread,
    )
    return SuccessResponse(
        data=[NotificationResponse.model_validate(n) for n in notifications],
        message=f"{len(notifications)} notification(s) found",
    )
