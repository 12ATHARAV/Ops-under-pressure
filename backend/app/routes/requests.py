from uuid import UUID
from typing import Optional, Any
from fastapi import APIRouter, Depends, Header, Query, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.db import get_db
from app.models.user import User
from app.models.team import TeamMembership
from app.models.request import Request
from app.models.event import RequestEvent
from app.schemas.common import PaginatedResponse, encode_cursor, decode_cursor
from app.schemas.request import (
    RequestCreate,
    RequestEdit,
    RequestAssign,
    RequestTransition,
    CommentCreate,
    CommentOut,
    RequestListOut,
    RequestDetailOut,
)
from app.schemas.event import RequestEventOut
from app.auth.deps import get_current_user
from app.services.requests import (
    create_request,
    edit_request,
    claim_request,
    transition_request,
    assign_request,
    get_request_with_access,
    compute_allowed_actions,
    request_to_dict,
)
from app.services.comments import add_comment
from app.services.queries import list_requests
from app.services.idempotency import with_idempotency

router = APIRouter(prefix="/requests", tags=["Requests"])


def format_request_detail(req: Request, user: User, membership: TeamMembership) -> dict[str, Any]:
    """Helper to convert a Request object and user context into a full RequestDetailOut dict."""
    allowed_actions = compute_allowed_actions(user, req, membership)
    comments_out = [
        {
            "id": str(c.id),
            "request_id": str(c.request_id),
            "author_id": str(c.author_id),
            "author_name": c.author.name if c.author else None,
            "body": c.body,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in (req.comments or [])
    ]
    data = request_to_dict(req)
    data["allowed_actions"] = allowed_actions
    data["sla_hours"] = req.request_type.sla_hours if req.request_type else None
    data["comments"] = comments_out
    return data


@router.get("", response_model=PaginatedResponse[RequestListOut])
def get_requests(
    team: Optional[UUID] = Query(None, description="Filter by team UUID"),
    status: Optional[str] = Query(None, description="Filter by request status"),
    owner: Optional[str] = Query(None, description="'me', 'none', or owner UUID"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    type: Optional[UUID] = Query(None, description="Filter by request type UUID"),
    q: Optional[str] = Query(None, description="Full-text search query"),
    cursor: Optional[str] = Query(None, description="Keyset pagination cursor"),
    limit: int = Query(25, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, next_cursor, has_more = list_requests(
        session=db,
        user=current_user,
        team_id=team,
        status=status,
        owner=owner,
        priority=priority,
        type_id=type,
        q=q,
        cursor=cursor,
        limit=limit,
    )
    return PaginatedResponse(
        items=[RequestListOut(**item) for item in items],
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_new_request(
    payload: RequestCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    def operation():
        req = create_request(
            session=db,
            user=current_user,
            team_id=payload.team_id,
            type_id=payload.type_id,
            title=payload.title,
            description=payload.description,
            priority=payload.priority,
        )
        membership = next(m for m in current_user.memberships if m.team_id == req.team_id)
        detail = format_request_detail(req, current_user, membership)
        return status.HTTP_201_CREATED, detail

    resp_status, body = with_idempotency(
        session=db,
        user_id=current_user.id,
        key=idempotency_key,
        endpoint="POST /requests",
        payload=payload.model_dump(),
        operation_fn=operation,
    )
    return JSONResponse(status_code=resp_status, content=jsonable_encoder(body))


@router.get("/{request_id}", response_model=RequestDetailOut)
def get_request_detail(
    request_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req, membership = get_request_with_access(db, current_user, request_id)
    return format_request_detail(req, current_user, membership)


@router.patch("/{request_id}", response_model=RequestDetailOut)
def update_request_fields(
    request_id: UUID,
    payload: RequestEdit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req = edit_request(
        session=db,
        user=current_user,
        request_id=request_id,
        client_version=payload.version,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        due_at=payload.due_at,
    )
    membership = next(m for m in current_user.memberships if m.team_id == req.team_id)
    return format_request_detail(req, current_user, membership)


@router.post("/{request_id}/claim")
def claim_existing_request(
    request_id: UUID,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    def operation():
        req = claim_request(session=db, user=current_user, request_id=request_id)
        membership = next(m for m in current_user.memberships if m.team_id == req.team_id)
        detail = format_request_detail(req, current_user, membership)
        return status.HTTP_200_OK, detail

    resp_status, body = with_idempotency(
        session=db,
        user_id=current_user.id,
        key=idempotency_key,
        endpoint=f"POST /requests/{request_id}/claim",
        payload={"request_id": str(request_id)},
        operation_fn=operation,
    )
    return JSONResponse(status_code=resp_status, content=jsonable_encoder(body))


@router.post("/{request_id}/assign", response_model=RequestDetailOut)
def assign_request_owner(
    request_id: UUID,
    payload: RequestAssign,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req = assign_request(
        session=db,
        user=current_user,
        request_id=request_id,
        new_owner_id=payload.owner_id,
        client_version=payload.version,
        reason=payload.reason,
    )
    membership = next(m for m in current_user.memberships if m.team_id == req.team_id)
    return format_request_detail(req, current_user, membership)


@router.post("/{request_id}/transition")
def transition_request_state(
    request_id: UUID,
    payload: RequestTransition,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    def operation():
        req = transition_request(
            session=db,
            user=current_user,
            request_id=request_id,
            target_status=payload.to,
            client_version=payload.version,
            reason=payload.reason,
        )
        membership = next(m for m in current_user.memberships if m.team_id == req.team_id)
        detail = format_request_detail(req, current_user, membership)
        return status.HTTP_200_OK, detail

    resp_status, body = with_idempotency(
        session=db,
        user_id=current_user.id,
        key=idempotency_key,
        endpoint=f"POST /requests/{request_id}/transition",
        payload=payload.model_dump(),
        operation_fn=operation,
    )
    return JSONResponse(status_code=resp_status, content=jsonable_encoder(body))


@router.get("/{request_id}/events", response_model=PaginatedResponse[RequestEventOut])
def get_request_timeline(
    request_id: UUID,
    cursor: Optional[int] = Query(None, description="Last seen event ID for pagination"),
    limit: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify access to the request first
    get_request_with_access(db, current_user, request_id)

    query = (
        db.query(RequestEvent)
        .options(joinedload(RequestEvent.actor))
        .filter(RequestEvent.request_id == request_id)
    )

    if cursor is not None:
        query = query.filter(RequestEvent.id < cursor)

    query = query.order_by(desc(RequestEvent.id))
    rows = query.limit(limit + 1).all()

    has_more = len(rows) > limit
    results = rows[:limit]
    next_cursor = str(results[-1].id) if has_more and results else None

    items = [
        RequestEventOut(
            id=e.id,
            request_id=e.request_id,
            actor_id=e.actor_id,
            actor_name=e.actor.name if e.actor else None,
            type=e.type,
            from_value=e.from_value,
            to_value=e.to_value,
            reason=e.reason,
            created_at=e.created_at,
        )
        for e in results
    ]

    return PaginatedResponse(
        items=items,
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.post("/{request_id}/comments", response_model=CommentOut)
def post_request_comment(
    request_id: UUID,
    payload: CommentCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    def operation():
        comment = add_comment(
            session=db,
            user=current_user,
            request_id=request_id,
            body=payload.body,
        )
        out = CommentOut(
            id=comment.id,
            request_id=comment.request_id,
            author_id=comment.author_id,
            author_name=current_user.name,
            body=comment.body,
            created_at=comment.created_at,
        )
        return status.HTTP_201_CREATED, out.model_dump()

    resp_status, body = with_idempotency(
        session=db,
        user_id=current_user.id,
        key=idempotency_key,
        endpoint=f"POST /requests/{request_id}/comments",
        payload=payload.model_dump(),
        operation_fn=operation,
    )
    return JSONResponse(status_code=resp_status, content=jsonable_encoder(body))
