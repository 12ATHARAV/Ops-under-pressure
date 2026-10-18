from uuid import UUID
from typing import Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from app.models.event import RequestEvent
from app.models.outbox import OutboxEntry, OutboxStatus


def append_event(
    session: Session,
    request_id: UUID,
    actor_id: UUID,
    type: str,
    from_val: Optional[Any] = None,
    to_val: Optional[Any] = None,
    reason: Optional[str] = None,
) -> RequestEvent:
    """Appends an immutable event row to the audit trail within the active transaction."""
    event = RequestEvent(
        request_id=request_id,
        actor_id=actor_id,
        type=type,
        from_value=from_val,
        to_value=to_val,
        reason=reason,
    )
    session.add(event)
    session.flush()  # Ensures event.id is generated for outbox referencing
    return event


def enqueue_outbox(
    session: Session,
    event_id: Optional[int],
    topic: str,
    payload: dict[str, Any],
) -> OutboxEntry:
    """Enqueues an outbox entry within the active transaction for reliable async processing."""
    entry = OutboxEntry(
        event_id=event_id,
        topic=topic,
        payload=payload,
        status=OutboxStatus.pending,
        attempts=0,
        next_attempt_at=func.now(),
    )
    session.add(entry)
    session.flush()
    return entry
