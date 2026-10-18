from uuid import UUID
from datetime import datetime
from typing import Optional, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, text
from app.models.user import User
from app.models.team import TeamMembership, TeamRole
from app.models.request import Request, RequestStatus, RequestPriority
from app.schemas.common import encode_cursor, decode_cursor
from app.services.requests import request_to_dict


def list_requests(
    session: Session,
    user: User,
    team_id: Optional[UUID] = None,
    status: Optional[str] = None,
    owner: Optional[str] = None,  # "me", "none", or a UUID string
    priority: Optional[str] = None,
    type_id: Optional[UUID] = None,
    q: Optional[str] = None,
    cursor: Optional[str] = None,
    limit: int = 25,
) -> tuple[list[dict[str, Any]], Optional[str], bool]:
    """
    Keyset paginated list of requests scoped to user's team memberships.
    Uses limit + 1 pattern to eliminate extra COUNT queries.
    Keyset sorting: (last_activity_at DESC, id DESC).
    """
    # 1. Scope to user's teams
    user_team_ids = [m.team_id for m in user.memberships]
    if not user_team_ids:
        return [], None, False

    if team_id is not None:
        if team_id not in user_team_ids:
            return [], None, False
        query_team_ids = [team_id]
    else:
        query_team_ids = user_team_ids

    query = (
        session.query(Request)
        .options(
            joinedload(Request.team),
            joinedload(Request.request_type),
            joinedload(Request.owner),
            joinedload(Request.creator),
        )
        .filter(Request.team_id.in_(query_team_ids))
    )

    # 2. Status filter
    if status:
        query = query.filter(Request.status == status)

    # 3. Owner filter
    if owner:
        if owner.lower() == "me":
            query = query.filter(Request.owner_id == user.id)
        elif owner.lower() == "none":
            query = query.filter(Request.owner_id.is_(None))
        else:
            try:
                owner_uuid = UUID(owner)
                query = query.filter(Request.owner_id == owner_uuid)
            except ValueError:
                pass

    # 4. Priority filter
    if priority:
        query = query.filter(Request.priority == priority)

    # 5. Type filter
    if type_id:
        query = query.filter(Request.type_id == type_id)

    # 6. Full-text search
    if q and q.strip():
        search_term = q.strip()
        dialect_name = session.bind.dialect.name if session.bind else "postgresql"
        if dialect_name == "postgresql":
            query = query.filter(text("search_tsv @@ plainto_tsquery('english', :q)")).params(q=search_term)
        else:
            query = query.filter(
                Request.title.ilike(f"%{search_term}%") | Request.description.ilike(f"%{search_term}%")
            )

    # 7. Keyset cursor filter: (last_activity_at, id) < (cursor_ts, cursor_id)
    if cursor:
        try:
            cursor_ts, cursor_id_str = decode_cursor(cursor)
            cursor_uuid = UUID(cursor_id_str)
            query = query.filter(
                (Request.last_activity_at < cursor_ts)
                | (
                    (Request.last_activity_at == cursor_ts)
                    & (Request.id < cursor_uuid)
                )
            )
        except Exception:
            pass

    # Keyset order
    query = query.order_by(desc(Request.last_activity_at), desc(Request.id))

    # Fetch limit + 1 items
    effective_limit = min(max(1, limit), 100)
    rows = query.limit(effective_limit + 1).all()

    has_more = len(rows) > effective_limit
    result_rows = rows[:effective_limit]

    next_cursor = None
    if has_more and result_rows:
        last_item = result_rows[-1]
        next_cursor = encode_cursor(last_item.last_activity_at, last_item.id)

    return [request_to_dict(r) for r in result_rows], next_cursor, has_more


def get_approval_queue(session: Session, user: User) -> list[dict[str, Any]]:
    """
    Returns requests awaiting start or completion approval in teams where
    the caller has 'approver' or 'lead' role.
    """
    approver_lead_team_ids = [
        m.team_id
        for m in user.memberships
        if m.role in (TeamRole.approver, TeamRole.lead)
        or str(m.role.value if hasattr(m.role, "value") else m.role) in ("approver", "lead")
    ]

    if not approver_lead_team_ids:
        return []

    approval_statuses = [
        RequestStatus.awaiting_start_approval,
        RequestStatus.awaiting_completion_approval,
    ]

    rows = (
        session.query(Request)
        .options(
            joinedload(Request.team),
            joinedload(Request.request_type),
            joinedload(Request.owner),
            joinedload(Request.creator),
        )
        .filter(
            Request.team_id.in_(approver_lead_team_ids),
            Request.status.in_(approval_statuses),
        )
        .order_by(desc(Request.last_activity_at), desc(Request.id))
        .all()
    )

    results = []
    for r in rows:
        d = request_to_dict(r)
        # Add separation of duties flag for UI
        d["can_approve"] = r.owner_id is None or r.owner_id != user.id
        results.append(d)

    return results
