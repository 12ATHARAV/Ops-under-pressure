from uuid import UUID
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.db import get_db
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification import NotificationOut
from app.schemas.common import PaginatedResponse, encode_cursor, decode_cursor
from app.auth.deps import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=PaginatedResponse[NotificationOut])
def get_user_notifications(
    cursor: Optional[str] = Query(None, description="Keyset cursor"),
    limit: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
    )

    if cursor:
        try:
            cursor_ts, cursor_id_str = decode_cursor(cursor)
            cursor_uuid = UUID(cursor_id_str)
            query = query.filter(
                (Notification.created_at < cursor_ts)
                | (
                    (Notification.created_at == cursor_ts)
                    & (Notification.id < cursor_uuid)
                )
            )
        except Exception:
            pass

    query = query.order_by(desc(Notification.created_at), desc(Notification.id))
    rows = query.limit(limit + 1).all()

    has_more = len(rows) > limit
    results = rows[:limit]
    next_cursor = None
    if has_more and results:
        last = results[-1]
        next_cursor = encode_cursor(last.created_at, last.id)

    items = [
        NotificationOut(
            id=n.id,
            user_id=n.user_id,
            request_id=n.request_id,
            kind=n.kind,
            body=n.body,
            read_at=n.read_at,
            dedupe_key=n.dedupe_key,
            created_at=n.created_at,
        )
        for n in results
    ]

    return PaginatedResponse(
        items=items,
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notif = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    if not notif.read_at:
        notif.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notif)

    return NotificationOut(
        id=notif.id,
        user_id=notif.user_id,
        request_id=notif.request_id,
        kind=notif.kind,
        body=notif.body,
        read_at=notif.read_at,
        dedupe_key=notif.dedupe_key,
        created_at=notif.created_at,
    )
