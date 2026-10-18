import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.models.outbox import OutboxEntry, OutboxStatus
from app.models.notification import Notification
from app.models.user import User
from app.models.request import Request
from app.worker.outbox_worker import process_outbox_batch, handle_outbox_entry
from app.config import settings


def test_outbox_processing_and_idempotent_notifications(db_session: Session):
    """
    Processing an outbox entry produces notifications.
    Running the processor again on the same event produces NO duplicate notifications
    due to unique dedupe_key.
    """
    user = db_session.query(User).filter(User.email == "alice@example.com").first()
    real_req = db_session.query(Request).first()

    # Create test outbox entry with event_id=None (entry.id will be used as fallback)
    entry = OutboxEntry(
        event_id=None,
        topic="request.assigned",
        payload={
            "request_id": str(real_req.id) if real_req else None,
            "title": "Outbox test item",
            "new_owner_id": str(user.id),
            "assigned_by_name": "Test Runner",
        },
        status=OutboxStatus.pending,
        attempts=0,
        next_attempt_at=datetime.now(timezone.utc) - timedelta(seconds=10),
    )
    db_session.add(entry)
    db_session.commit()
    db_session.refresh(entry)

    # 1. Process outbox
    processed_count = process_outbox_batch(db_session, limit=100)
    assert processed_count >= 1

    db_session.refresh(entry)
    assert entry.status == OutboxStatus.done

    # Verify notification created
    notifs = db_session.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.dedupe_key == f"{entry.id}:{user.id}:request_assigned",
    ).all()
    assert len(notifs) == 1

    # 2. Simulate re-running handler on same event
    handle_outbox_entry(db_session, entry)
    db_session.commit()

    # Verify still exactly 1 notification
    notifs_after = db_session.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.dedupe_key == f"{entry.id}:{user.id}:request_assigned",
    ).all()
    assert len(notifs_after) == 1


def test_outbox_poison_job_dead_lettering(db_session: Session):
    """
    A permanently failing outbox job increments attempts and eventually
    transitions to 'dead' status after settings.OUTBOX_MAX_ATTEMPTS.
    """
    # Create an entry with invalid payload to trigger handler error
    entry = OutboxEntry(
        event_id=None,
        topic="request.assigned",
        payload={"new_owner_id": "not-a-valid-uuid"},  # Causes ValueError in UUID parse
        status=OutboxStatus.pending,
        attempts=settings.OUTBOX_MAX_ATTEMPTS - 1,  # 1 attempt left before dead
        next_attempt_at=datetime.now(timezone.utc) - timedelta(seconds=10),
    )
    db_session.add(entry)
    db_session.commit()
    db_session.refresh(entry)

    # Process outbox batch
    process_outbox_batch(db_session, limit=100)

    db_session.refresh(entry)
    assert entry.status == OutboxStatus.dead
    assert entry.last_error is not None
    assert entry.attempts >= settings.OUTBOX_MAX_ATTEMPTS
