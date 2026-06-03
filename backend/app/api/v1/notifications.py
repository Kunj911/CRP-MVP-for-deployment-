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


@router.post(
    "/notifications/{notification_id}/read",
    response_model=SuccessResponse[bool],
    summary="Mark notification as read",
    description="Mark a specific in-app notification as read."
)
def mark_read(
    notification_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[bool]:
    success = notification_service.mark_notification_as_read(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id
    )
    if not success:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("Notification", notification_id)
    return SuccessResponse(data=True, message="Notification marked as read")


@router.post(
    "/notifications/read-all",
    response_model=SuccessResponse[int],
    summary="Mark all notifications as read",
    description="Mark all unread in-app notifications for the current user as read."
)
def mark_all_read(
    current_user: CurrentUser,
    db: DbSession,
) -> SuccessResponse[int]:
    count = notification_service.mark_all_notifications_as_read(
        db=db,
        user_id=current_user.id
    )
    return SuccessResponse(data=count, message=f"Marked {count} notification(s) as read")

