import time
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import settings
from app.db import SessionLocal
from app.models.outbox import OutboxEntry, OutboxStatus
from app.models.notification import Notification
from app.models.team import TeamMembership, TeamRole
from app.models.request import Request

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("outbox_worker")


def insert_notification_idempotent(
    session: Session,
    user_id: UUID,
    request_id: Optional[UUID],
    kind: str,
    body: str,
    dedupe_key: str,
) -> None:
    """Inserts a notification using ON CONFLICT (dedupe_key) DO NOTHING to ensure idempotency."""
    dialect_name = session.bind.dialect.name if session.bind else "postgresql"
    if dialect_name == "postgresql":
        stmt = (
            pg_insert(Notification)
            .values(
                id=uuid.uuid4(),
                user_id=user_id,
                request_id=request_id,
                kind=kind,
                body=body,
                dedupe_key=dedupe_key,
                created_at=func.now(),
            )
            .on_conflict_do_nothing(index_elements=["dedupe_key"])
        )
        session.execute(stmt)
    else:
        existing = session.query(Notification).filter(Notification.dedupe_key == dedupe_key).first()
        if not existing:
            notif = Notification(
                id=uuid.uuid4(),
                user_id=user_id,
                request_id=request_id,
                kind=kind,
                body=body,
                dedupe_key=dedupe_key,
            )
            session.add(notif)
            try:
                session.flush()
            except Exception:
                pass


def handle_outbox_entry(session: Session, entry: OutboxEntry) -> None:
    """Processes an individual outbox entry and generates relevant notifications."""
    payload = entry.payload or {}
    topic = entry.topic
    event_id = entry.event_id or entry.id
    req_id_str = payload.get("request_id")
    req_uuid = UUID(req_id_str) if req_id_str else None
    team_id_str = payload.get("team_id")
    team_uuid = UUID(team_id_str) if team_id_str else None
    title = payload.get("title", "Request")

    if topic == "request.created":
        # Notify team leads
        if team_uuid:
            leads = (
                session.query(TeamMembership)
                .filter(TeamMembership.team_id == team_uuid, TeamMembership.role == TeamRole.lead)
                .all()
            )
            creator_name = payload.get("creator_name", "A user")
            for lead in leads:
                dedupe_key = f"{event_id}:{lead.user_id}:request_created"
                body = f"New request '{title}' was submitted by {creator_name}"
                insert_notification_idempotent(session, lead.user_id, req_uuid, "request_created", body, dedupe_key)

    elif topic == "request.claimed":
        claimed_by_id = payload.get("claimed_by_id")
        claimed_by_name = payload.get("claimed_by_name", "A user")
        if team_uuid:
            leads = (
                session.query(TeamMembership)
                .filter(TeamMembership.team_id == team_uuid, TeamMembership.role == TeamRole.lead)
                .all()
            )
            for lead in leads:
                if str(lead.user_id) != claimed_by_id:
                    dedupe_key = f"{event_id}:{lead.user_id}:request_claimed"
                    body = f"Request '{title}' was claimed by {claimed_by_name}"
                    insert_notification_idempotent(session, lead.user_id, req_uuid, "request_claimed", body, dedupe_key)

    elif topic == "request.assigned":
        new_owner_id_str = payload.get("new_owner_id")
        assigned_by_name = payload.get("assigned_by_name", "Lead")
        if new_owner_id_str:
            new_owner_uuid = UUID(new_owner_id_str)
            dedupe_key = f"{event_id}:{new_owner_uuid}:request_assigned"
            body = f"You were assigned request '{title}' by {assigned_by_name}"
            insert_notification_idempotent(session, new_owner_uuid, req_uuid, "request_assigned", body, dedupe_key)

    elif topic == "request.status_changed":
        from_status = payload.get("from_status")
        to_status = payload.get("to_status")
        owner_id_str = payload.get("owner_id")
        created_by_str = payload.get("created_by")
        reason = payload.get("reason")
        actor_name = payload.get("actor_name", "An approver")

        # 1. Approval needed notifications to approvers and leads
        if to_status in ("awaiting_start_approval", "awaiting_completion_approval"):
            if team_uuid:
                approvers = (
                    session.query(TeamMembership)
                    .filter(
                        TeamMembership.team_id == team_uuid,
                        TeamMembership.role.in_([TeamRole.approver, TeamRole.lead]),
                    )
                    .all()
                )
                for app_m in approvers:
                    # Separation of duties: don't notify owner to approve their own request
                    if owner_id_str and str(app_m.user_id) == owner_id_str:
                        continue
                    dedupe_key = f"{event_id}:{app_m.user_id}:approval_needed"
                    body = f"Approval required for request '{title}' to move to '{to_status}'"
                    insert_notification_idempotent(session, app_m.user_id, req_uuid, "approval_needed", body, dedupe_key)

        # 2. Approved / rejected notifications to the owner
        if owner_id_str:
            owner_uuid = UUID(owner_id_str)
            if from_status == "awaiting_start_approval" and to_status == "in_progress":
                dedupe_key = f"{event_id}:{owner_uuid}:start_approved"
                body = f"Start approval granted for '{title}' by {actor_name}"
                insert_notification_idempotent(session, owner_uuid, req_uuid, "start_approved", body, dedupe_key)
            elif from_status == "awaiting_start_approval" and to_status == "triage":
                dedupe_key = f"{event_id}:{owner_uuid}:start_rejected"
                body = f"Start approval rejected for '{title}': {reason or 'No reason provided'}"
                insert_notification_idempotent(session, owner_uuid, req_uuid, "start_rejected", body, dedupe_key)
            elif from_status == "awaiting_completion_approval" and to_status == "in_progress":
                dedupe_key = f"{event_id}:{owner_uuid}:completion_rejected"
                body = f"Completion approval rejected for '{title}': {reason or 'No reason provided'}"
                insert_notification_idempotent(session, owner_uuid, req_uuid, "completion_rejected", body, dedupe_key)

        # 3. Terminal state notifications
        recipients = set()
        if owner_id_str:
            recipients.add(UUID(owner_id_str))
        if created_by_str:
            recipients.add(UUID(created_by_str))

        if to_status == "done":
            for recipient_id in recipients:
                dedupe_key = f"{event_id}:{recipient_id}:request_completed"
                body = f"Request '{title}' has been completed"
                insert_notification_idempotent(session, recipient_id, req_uuid, "request_completed", body, dedupe_key)
        elif to_status == "cancelled":
            for recipient_id in recipients:
                dedupe_key = f"{event_id}:{recipient_id}:request_cancelled"
                body = f"Request '{title}' was cancelled: {reason or 'No reason provided'}"
                insert_notification_idempotent(session, recipient_id, req_uuid, "request_cancelled", body, dedupe_key)

    elif topic == "request.commented":
        author_id_str = payload.get("author_id")
        author_name = payload.get("author_name", "A colleague")
        preview = payload.get("comment_preview", "")
        # Notify owner and creator (if not the author)
        if req_uuid:
            req = session.query(Request).filter(Request.id == req_uuid).first()
            if req:
                notify_users = set()
                if req.owner_id and str(req.owner_id) != author_id_str:
                    notify_users.add(req.owner_id)
                if req.created_by and str(req.created_by) != author_id_str:
                    notify_users.add(req.created_by)

                for u_id in notify_users:
                    dedupe_key = f"{event_id}:{u_id}:comment_added"
                    body = f"{author_name} commented on '{title}': \"{preview}\""
                    insert_notification_idempotent(session, u_id, req_uuid, "comment_added", body, dedupe_key)


def process_outbox_batch(session: Session, limit: int = 20) -> int:
    """
    Selects pending outbox rows with FOR UPDATE SKIP LOCKED, executes handlers,
    applies exponential backoff on failure, and marks completed or dead.
    Returns the count of processed entries.
    """
    now = datetime.now(timezone.utc)
    dialect_name = session.bind.dialect.name if session.bind else "postgresql"

    query = session.query(OutboxEntry).filter(
        OutboxEntry.status == OutboxStatus.pending,
        OutboxEntry.next_attempt_at <= now,
    )

    if dialect_name == "postgresql":
        query = query.with_for_update(skip_locked=True)

    entries = query.order_by(OutboxEntry.id).limit(limit).all()
    if not entries:
        return 0

    for entry in entries:
        try:
            handle_outbox_entry(session, entry)
            entry.status = OutboxStatus.done
            entry.attempts += 1
            session.commit()
            logger.info(f"Processed outbox entry id={entry.id} topic={entry.topic}")
        except Exception as e:
            session.rollback()
            # Fetch fresh reference in rolled-back session
            failed_entry = session.query(OutboxEntry).filter(OutboxEntry.id == entry.id).first()
            if failed_entry:
                failed_entry.attempts += 1
                failed_entry.last_error = str(e)
                if failed_entry.attempts >= settings.OUTBOX_MAX_ATTEMPTS:
                    failed_entry.status = OutboxStatus.dead
                    logger.error(f"Outbox entry id={failed_entry.id} marked DEAD after {failed_entry.attempts} attempts: {e}")
                else:
                    backoff_seconds = 2 ** failed_entry.attempts
                    failed_entry.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds)
                    logger.warning(
                        f"Outbox entry id={failed_entry.id} failed (attempt {failed_entry.attempts}), retrying in {backoff_seconds}s: {e}"
                    )
                session.commit()

    return len(entries)


def run_worker(max_iterations: Optional[int] = None) -> None:
    """Main worker loop polling outbox table."""
    logger.info("Outbox worker started. Polling for pending events...")
    iterations = 0
    while True:
        session: Session = SessionLocal()
        try:
            count = process_outbox_batch(session, limit=20)
        except Exception as e:
            logger.error(f"Unexpected error in outbox worker poll loop: {e}", exc_info=True)
            count = 0
        finally:
            session.close()

        iterations += 1
        if max_iterations is not None and iterations >= max_iterations:
            logger.info(f"Reached max_iterations={max_iterations}. Exiting worker.")
            break

        if count == 0:
            time.sleep(settings.OUTBOX_POLL_INTERVAL)


if __name__ == "__main__":
    run_worker()
