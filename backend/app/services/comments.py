from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload
from app.models.user import User
from app.models.request import Comment, Request
from app.services.requests import get_request_with_access
from app.services.events import append_event, enqueue_outbox


def add_comment(
    session: Session,
    user: User,
    request_id: UUID,
    body: str,
) -> Comment:
    """Adds a comment to a request, touches last_activity_at, logs event, and enqueues outbox."""
    req, membership = get_request_with_access(session, user, request_id)

    now = datetime.now(timezone.utc)
    comment = Comment(
        request_id=request_id,
        author_id=user.id,
        body=body,
        created_at=now,
    )
    session.add(comment)

    # Touch request last_activity_at
    req.last_activity_at = now
    session.flush()

    # Append event
    event = append_event(
        session,
        request_id=request_id,
        actor_id=user.id,
        type="commented",
        from_val=None,
        to_val={"comment_id": str(comment.id), "body": body},
        reason=None,
    )

    # Enqueue outbox
    enqueue_outbox(
        session,
        event_id=event.id,
        topic="request.commented",
        payload={
            "request_id": str(request_id),
            "team_id": str(req.team_id),
            "title": req.title,
            "comment_id": str(comment.id),
            "author_id": str(user.id),
            "author_name": user.name,
            "comment_preview": (body[:100] + "...") if len(body) > 100 else body,
        },
    )

    session.commit()
    # Refresh comment with author relationship
    loaded_comment = (
        session.query(Comment)
        .options(joinedload(Comment.author))
        .filter(Comment.id == comment.id)
        .first()
    )
    return loaded_comment or comment
