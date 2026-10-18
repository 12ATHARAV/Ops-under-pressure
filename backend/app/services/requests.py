from uuid import UUID
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import update, desc
from sqlalchemy.sql import func
from app.models.user import User
from app.models.team import TeamMembership, TeamRole
from app.models.request import (
    Request,
    RequestType,
    RequestStatus,
    RequestPriority,
    ApprovalMode,
)
from app.models.event import RequestEvent
from app.authz.policy import authorize, NotFoundError, ForbiddenError
from app.workflow.transitions import (
    validate_transition,
    IllegalTransition,
    Forbidden,
    ValidationError as WorkflowValidationError,
    TRANSITIONS,
    TERMINAL_STATES,
)
from app.services.events import append_event, enqueue_outbox


class VersionConflict(Exception):
    """Raised when an update fails due to version mismatch (optimistic locking conflict) (409)."""

    def __init__(self, current: dict[str, Any], events_since_version: list[dict[str, Any]]):
        self.current = current
        self.events_since_version = events_since_version
        super().__init__("Request was modified by another transaction")


class AlreadyClaimed(Exception):
    """Raised when an atomic claim fails because the request is already claimed (409)."""

    def __init__(self, message: str, owner_name: Optional[str] = None):
        self.owner_name = owner_name
        super().__init__(message)


def request_to_dict(req: Request) -> dict[str, Any]:
    """Helper to convert a Request object to a JSON-serializable dictionary."""
    return {
        "id": str(req.id),
        "team_id": str(req.team_id),
        "team_name": req.team.name if req.team else None,
        "type_id": str(req.type_id),
        "type_name": req.request_type.name if req.request_type else None,
        "approval_mode": req.request_type.approval_mode.value if req.request_type else None,
        "title": req.title,
        "description": req.description,
        "status": req.status.value if hasattr(req.status, "value") else str(req.status),
        "priority": req.priority.value if hasattr(req.priority, "value") else str(req.priority),
        "owner_id": str(req.owner_id) if req.owner_id else None,
        "owner_name": req.owner.name if req.owner else None,
        "created_by": str(req.created_by),
        "creator_name": req.creator.name if req.creator else None,
        "version": req.version,
        "due_at": req.due_at.isoformat() if req.due_at else None,
        "last_activity_at": req.last_activity_at.isoformat() if req.last_activity_at else None,
        "created_at": req.created_at.isoformat() if req.created_at else None,
        "updated_at": req.updated_at.isoformat() if req.updated_at else None,
    }


def event_to_dict(e: RequestEvent) -> dict[str, Any]:
    """Helper to convert a RequestEvent object to a JSON-serializable dictionary."""
    return {
        "id": e.id,
        "request_id": str(e.request_id),
        "actor_id": str(e.actor_id),
        "actor_name": e.actor.name if e.actor else None,
        "type": e.type,
        "from_value": e.from_value,
        "to_value": e.to_value,
        "reason": e.reason,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def compute_allowed_actions(user: User, req: Request, membership: TeamMembership) -> list[str]:
    """Calculates permissible actions for the current user on the given request."""
    actions = []
    current_status = req.status.value if hasattr(req.status, "value") else str(req.status)
    is_terminal = current_status in TERMINAL_STATES
    actor_role = membership.role.value if hasattr(membership.role, "value") else str(membership.role)
    is_owner = req.owner_id is not None and req.owner_id == user.id
    is_lead = actor_role == "lead"
    is_approver_or_lead = actor_role in ("approver", "lead")

    # Commenting is allowed for all team members
    actions.append("comment")

    # Claiming
    if req.owner_id is None and current_status in ("new", "triage"):
        actions.append("claim")

    # Editing
    if not is_terminal and (is_lead or is_owner):
        actions.append("edit")

    # Assigning
    if not is_terminal and is_lead:
        actions.append("assign")

    # Cancelling
    if not is_terminal and (is_lead or (current_status == "new" and req.created_by == user.id)):
        actions.append("cancel")

    # Status transitions
    for (from_s, to_s) in TRANSITIONS.keys():
        if from_s == current_status:
            try:
                # Test if transition is valid
                validate_transition(req, to_s, user, membership, reason="check")
                actions.append(f"transition:{to_s}")
            except Exception:
                pass

    return actions


def get_request_with_access(session: Session, user: User, request_id: UUID) -> tuple[Request, TeamMembership]:
    """Fetches a request and verifies the caller's team membership, returning (request, membership)."""
    req = (
        session.query(Request)
        .options(
            joinedload(Request.team),
            joinedload(Request.request_type),
            joinedload(Request.owner),
            joinedload(Request.creator),
            joinedload(Request.comments),
        )
        .filter(Request.id == request_id)
        .first()
    )
    if not req:
        raise NotFoundError(f"Request {request_id} not found")

    membership = (
        session.query(TeamMembership)
        .filter(TeamMembership.user_id == user.id, TeamMembership.team_id == req.team_id)
        .first()
    )
    if not membership:
        raise NotFoundError(f"Request {request_id} not found")

    return req, membership


def create_request(
    session: Session,
    user: User,
    team_id: UUID,
    type_id: UUID,
    title: str,
    description: str = "",
    priority: RequestPriority = RequestPriority.medium,
) -> Request:
    """Creates a new request, appends a creation event, and enqueues outbox atomically."""
    # Verify user is member of the team
    membership = (
        session.query(TeamMembership)
        .filter(TeamMembership.user_id == user.id, TeamMembership.team_id == team_id)
        .first()
    )
    if not membership:
        raise NotFoundError("Team not found or user is not a member")

    req_type = (
        session.query(RequestType)
        .filter(RequestType.id == type_id, RequestType.team_id == team_id)
        .first()
    )
    if not req_type:
        raise WorkflowValidationError("Request type not found for this team")

    now = datetime.now(timezone.utc)
    due_at = now + timedelta(hours=req_type.sla_hours) if req_type.sla_hours else None

    req = Request(
        team_id=team_id,
        type_id=type_id,
        title=title,
        description=description,
        status=RequestStatus.new,
        priority=priority,
        owner_id=None,
        created_by=user.id,
        version=1,
        due_at=due_at,
        last_activity_at=now,
    )
    session.add(req)
    session.flush()

    # Append event
    event = append_event(
        session,
        request_id=req.id,
        actor_id=user.id,
        type="created",
        from_val=None,
        to_val={"title": req.title, "status": "new", "priority": req.priority.value},
        reason=None,
    )

    # Enqueue outbox
    enqueue_outbox(
        session,
        event_id=event.id,
        topic="request.created",
        payload={
            "request_id": str(req.id),
            "team_id": str(team_id),
            "title": req.title,
            "created_by": str(user.id),
            "creator_name": user.name,
        },
    )

    session.commit()
    session.expire_all()
    # Refresh to load relationships
    req_loaded, _ = get_request_with_access(session, user, req.id)
    return req_loaded


def claim_request(
    session: Session,
    user: User,
    request_id: UUID,
) -> Request:
    """
    Atomically claims an unowned request using conditional UPDATE ... WHERE owner_id IS NULL.
    Guarantees exactly one winner under concurrent attempts.
    """
    req, membership = get_request_with_access(session, user, request_id)

    # Atomic claim in SQL
    now = datetime.now(timezone.utc)
    result = session.execute(
        update(Request)
        .where(Request.id == request_id, Request.owner_id.is_(None))
        .values(
            owner_id=user.id,
            version=Request.version + 1,
            last_activity_at=now,
        )
    )

    if result.rowcount == 0:
        session.rollback()
        # Fetch current owner to return informative error
        current_req = session.query(Request).filter(Request.id == request_id).first()
        owner_name = current_req.owner.name if current_req and current_req.owner else "another user"
        raise AlreadyClaimed(f"Request is already claimed by {owner_name}", owner_name=owner_name)

    # Append event
    event = append_event(
        session,
        request_id=request_id,
        actor_id=user.id,
        type="owner_changed",
        from_val={"owner_id": None, "owner_name": None},
        to_val={"owner_id": str(user.id), "owner_name": user.name},
        reason="Claimed work item",
    )

    # Enqueue outbox
    enqueue_outbox(
        session,
        event_id=event.id,
        topic="request.claimed",
        payload={
            "request_id": str(request_id),
            "team_id": str(req.team_id),
            "title": req.title,
            "claimed_by_id": str(user.id),
            "claimed_by_name": user.name,
        },
    )

    session.commit()
    session.expire_all()
    updated_req, _ = get_request_with_access(session, user, request_id)
    return updated_req


def edit_request(
    session: Session,
    user: User,
    request_id: UUID,
    client_version: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[RequestPriority] = None,
    due_at: Optional[datetime] = None,
) -> Request:
    """Edits request fields with optimistic locking verification."""
    req, membership = get_request_with_access(session, user, request_id)
    authorize(user, req, "edit")

    now = datetime.now(timezone.utc)
    values_to_update: dict[str, Any] = {
        "version": Request.version + 1,
        "last_activity_at": now,
    }
    from_vals: dict[str, Any] = {}
    to_vals: dict[str, Any] = {}

    if title is not None and title != req.title:
        values_to_update["title"] = title
        from_vals["title"] = req.title
        to_vals["title"] = title

    if description is not None and description != req.description:
        values_to_update["description"] = description
        from_vals["description"] = req.description
        to_vals["description"] = description

    if priority is not None and priority != req.priority:
        values_to_update["priority"] = priority
        from_vals["priority"] = req.priority.value if hasattr(req.priority, "value") else req.priority
        to_vals["priority"] = priority.value if hasattr(priority, "value") else priority

    if due_at is not None and due_at != req.due_at:
        values_to_update["due_at"] = due_at
        from_vals["due_at"] = req.due_at.isoformat() if req.due_at else None
        to_vals["due_at"] = due_at.isoformat() if due_at else None

    # Perform optimistic locking update
    result = session.execute(
        update(Request)
        .where(Request.id == request_id, Request.version == client_version)
        .values(**values_to_update)
    )

    if result.rowcount == 0:
        session.rollback()
        # Build conflict details
        current_req, _ = get_request_with_access(session, user, request_id)
        events = (
            session.query(RequestEvent)
            .options(joinedload(RequestEvent.actor))
            .filter(RequestEvent.request_id == request_id)
            .order_by(desc(RequestEvent.id))
            .limit(10)
            .all()
        )
        raise VersionConflict(
            current=request_to_dict(current_req),
            events_since_version=[event_to_dict(e) for e in events],
        )

    event = append_event(
        session,
        request_id=request_id,
        actor_id=user.id,
        type="edited",
        from_val=from_vals,
        to_val=to_vals,
        reason="Updated request details",
    )

    enqueue_outbox(
        session,
        event_id=event.id,
        topic="request.updated",
        payload={
            "request_id": str(request_id),
            "team_id": str(req.team_id),
            "title": title or req.title,
            "actor_id": str(user.id),
            "actor_name": user.name,
        },
    )

    session.commit()
    session.expire_all()
    updated_req, _ = get_request_with_access(session, user, request_id)
    return updated_req


def transition_request(
    session: Session,
    user: User,
    request_id: UUID,
    target_status: str,
    client_version: int,
    reason: Optional[str] = None,
) -> Request:
    """
    Validates state machine rules, performs optimistic locking update,
    records event and enqueues outbox in a single transaction.
    """
    req, membership = get_request_with_access(session, user, request_id)

    # 1. State machine validation
    validate_transition(req, target_status, user, membership, reason=reason)

    old_status = req.status.value if hasattr(req.status, "value") else str(req.status)
    target_val = target_status.value if hasattr(target_status, "value") else str(target_status)
    now = datetime.now(timezone.utc)

    # 2. Optimistic lock update
    result = session.execute(
        update(Request)
        .where(Request.id == request_id, Request.version == client_version)
        .values(
            status=target_val,
            version=Request.version + 1,
            last_activity_at=now,
        )
    )

    if result.rowcount == 0:
        session.rollback()
        current_req, _ = get_request_with_access(session, user, request_id)
        events = (
            session.query(RequestEvent)
            .options(joinedload(RequestEvent.actor))
            .filter(RequestEvent.request_id == request_id)
            .order_by(desc(RequestEvent.id))
            .limit(10)
            .all()
        )
        raise VersionConflict(
            current=request_to_dict(current_req),
            events_since_version=[event_to_dict(e) for e in events],
        )

    # 3. Append history event
    event = append_event(
        session,
        request_id=request_id,
        actor_id=user.id,
        type="status_changed",
        from_val={"status": old_status},
        to_val={"status": target_val},
        reason=reason,
    )

    # 4. Outbox entry
    enqueue_outbox(
        session,
        event_id=event.id,
        topic="request.status_changed",
        payload={
            "request_id": str(request_id),
            "team_id": str(req.team_id),
            "title": req.title,
            "from_status": old_status,
            "to_status": target_val,
            "actor_id": str(user.id),
            "actor_name": user.name,
            "reason": reason,
            "owner_id": str(req.owner_id) if req.owner_id else None,
            "created_by": str(req.created_by),
        },
    )

    session.commit()
    session.expire_all()
    updated_req, _ = get_request_with_access(session, user, request_id)
    return updated_req


def assign_request(
    session: Session,
    user: User,
    request_id: UUID,
    new_owner_id: UUID,
    client_version: int,
    reason: Optional[str] = None,
) -> Request:
    """Lead-only reassignment of request owner with optimistic locking."""
    req, membership = get_request_with_access(session, user, request_id)
    authorize(user, req, "assign")

    # Verify new owner is a team member
    target_membership = (
        session.query(TeamMembership)
        .options(joinedload(TeamMembership.user))
        .filter(TeamMembership.user_id == new_owner_id, TeamMembership.team_id == req.team_id)
        .first()
    )
    if not target_membership:
        raise WorkflowValidationError("Assigned user is not a member of this team")

    old_owner_id = str(req.owner_id) if req.owner_id else None
    old_owner_name = req.owner.name if req.owner else None
    now = datetime.now(timezone.utc)

    result = session.execute(
        update(Request)
        .where(Request.id == request_id, Request.version == client_version)
        .values(
            owner_id=new_owner_id,
            version=Request.version + 1,
            last_activity_at=now,
        )
    )

    if result.rowcount == 0:
        session.rollback()
        current_req, _ = get_request_with_access(session, user, request_id)
        events = (
            session.query(RequestEvent)
            .options(joinedload(RequestEvent.actor))
            .filter(RequestEvent.request_id == request_id)
            .order_by(desc(RequestEvent.id))
            .limit(10)
            .all()
        )
        raise VersionConflict(
            current=request_to_dict(current_req),
            events_since_version=[event_to_dict(e) for e in events],
        )

    event = append_event(
        session,
        request_id=request_id,
        actor_id=user.id,
        type="owner_changed",
        from_val={"owner_id": old_owner_id, "owner_name": old_owner_name},
        to_val={"owner_id": str(new_owner_id), "owner_name": target_membership.user.name},
        reason=reason or "Reassigned by lead",
    )

    enqueue_outbox(
        session,
        event_id=event.id,
        topic="request.assigned",
        payload={
            "request_id": str(request_id),
            "team_id": str(req.team_id),
            "title": req.title,
            "new_owner_id": str(new_owner_id),
            "new_owner_name": target_membership.user.name,
            "assigned_by_id": str(user.id),
            "assigned_by_name": user.name,
            "reason": reason,
        },
    )

    session.commit()
    session.expire_all()
    updated_req, _ = get_request_with_access(session, user, request_id)
    return updated_req
