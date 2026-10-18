from datetime import datetime, timedelta, timezone
from typing import Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func
from app.config import settings
from app.models.user import User
from app.models.team import TeamMembership, TeamRole
from app.models.request import Request, RequestStatus, RequestPriority
from app.services.requests import request_to_dict


def get_attention_buckets(user: User, session: Session) -> dict[str, Any]:
    """
    Computes 'Needs Attention' buckets for a lead across their led teams:
    - unowned: in new/triage without owner, older than UNOWNED_HOURS
    - stale: active status, last_activity_at older than STALE_HOURS
    - overdue: due_at past and not terminal
    - stuck_approval: awaiting approval for longer than STUCK_APPROVAL_HOURS
    - urgent: urgent priority and not terminal
    """
    lead_team_ids = [
        m.team_id for m in user.memberships if m.role == TeamRole.lead or str(m.role.value if hasattr(m.role, "value") else m.role) == "lead"
    ]

    empty_result = {
        "unowned": {"count": 0, "items": []},
        "stale": {"count": 0, "items": []},
        "overdue": {"count": 0, "items": []},
        "stuck_approval": {"count": 0, "items": []},
        "urgent": {"count": 0, "items": []},
    }

    if not lead_team_ids:
        return empty_result

    now = datetime.now(timezone.utc)
    unowned_cutoff = now - timedelta(hours=settings.UNOWNED_HOURS)
    stale_cutoff = now - timedelta(hours=settings.STALE_HOURS)
    stuck_cutoff = now - timedelta(hours=settings.STUCK_APPROVAL_HOURS)

    base_query = (
        session.query(Request)
        .options(
            joinedload(Request.team),
            joinedload(Request.request_type),
            joinedload(Request.owner),
            joinedload(Request.creator),
        )
        .filter(Request.team_id.in_(lead_team_ids))
    )

    non_terminal_statuses = [
        RequestStatus.new,
        RequestStatus.triage,
        RequestStatus.awaiting_start_approval,
        RequestStatus.in_progress,
        RequestStatus.awaiting_completion_approval,
    ]

    # 1. Unowned
    unowned_filter = (
        Request.team_id.in_(lead_team_ids),
        Request.owner_id.is_(None),
        Request.status.in_([RequestStatus.new, RequestStatus.triage]),
        Request.created_at <= unowned_cutoff,
    )
    unowned_count = session.query(func.count(Request.id)).filter(*unowned_filter).scalar() or 0
    unowned_items = (
        base_query.filter(*unowned_filter)
        .order_by(desc(Request.created_at), desc(Request.id))
        .limit(10)
        .all()
    )

    # 2. Stale
    stale_filter = (
        Request.team_id.in_(lead_team_ids),
        Request.status.in_(non_terminal_statuses),
        Request.last_activity_at <= stale_cutoff,
    )
    stale_count = session.query(func.count(Request.id)).filter(*stale_filter).scalar() or 0
    stale_items = (
        base_query.filter(*stale_filter)
        .order_by(Request.last_activity_at.asc(), desc(Request.id))
        .limit(10)
        .all()
    )

    # 3. Overdue
    overdue_filter = (
        Request.team_id.in_(lead_team_ids),
        Request.due_at.is_not(None),
        Request.due_at <= now,
        Request.status.in_(non_terminal_statuses),
    )
    overdue_count = session.query(func.count(Request.id)).filter(*overdue_filter).scalar() or 0
    overdue_items = (
        base_query.filter(*overdue_filter)
        .order_by(Request.due_at.asc(), desc(Request.id))
        .limit(10)
        .all()
    )

    # 4. Stuck in approval
    approval_statuses = [
        RequestStatus.awaiting_start_approval,
        RequestStatus.awaiting_completion_approval,
    ]
    stuck_filter = (
        Request.team_id.in_(lead_team_ids),
        Request.status.in_(approval_statuses),
        Request.last_activity_at <= stuck_cutoff,
    )
    stuck_count = session.query(func.count(Request.id)).filter(*stuck_filter).scalar() or 0
    stuck_items = (
        base_query.filter(*stuck_filter)
        .order_by(Request.last_activity_at.asc(), desc(Request.id))
        .limit(10)
        .all()
    )

    # 5. Urgent
    urgent_filter = (
        Request.team_id.in_(lead_team_ids),
        Request.priority == RequestPriority.urgent,
        Request.status.in_(non_terminal_statuses),
    )
    urgent_count = session.query(func.count(Request.id)).filter(*urgent_filter).scalar() or 0
    urgent_items = (
        base_query.filter(*urgent_filter)
        .order_by(desc(Request.last_activity_at), desc(Request.id))
        .limit(10)
        .all()
    )

    return {
        "unowned": {
            "count": unowned_count,
            "items": [request_to_dict(r) for r in unowned_items],
        },
        "stale": {
            "count": stale_count,
            "items": [request_to_dict(r) for r in stale_items],
        },
        "overdue": {
            "count": overdue_count,
            "items": [request_to_dict(r) for r in overdue_items],
        },
        "stuck_approval": {
            "count": stuck_count,
            "items": [request_to_dict(r) for r in stuck_items],
        },
        "urgent": {
            "count": urgent_count,
            "items": [request_to_dict(r) for r in urgent_items],
        },
    }
