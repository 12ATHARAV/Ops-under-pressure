from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models.user import User
from app.models.team import Team, TeamMembership
from app.models.request import RequestType
from app.auth.deps import get_current_user

router = APIRouter(tags=["Teams & Metadata"])


@router.get("/teams")
def list_teams(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns teams the current user belongs to, or all teams if user has global visibility."""
    user_teams = (
        db.query(Team)
        .join(TeamMembership, TeamMembership.team_id == Team.id)
        .filter(TeamMembership.user_id == current_user.id)
        .order_by(Team.name)
        .all()
    )
    if not user_teams:
        user_teams = db.query(Team).order_by(Team.name).all()
    return [{"id": str(t.id), "name": t.name} for t in user_teams]


@router.get("/request-types")
def list_request_types(
    team_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns request types configured for teams."""
    query = db.query(RequestType)
    if team_id:
        query = query.filter(RequestType.team_id == team_id)
    types = query.order_by(RequestType.name).all()
    return [
        {
            "id": str(rt.id),
            "team_id": str(rt.team_id),
            "name": rt.name,
            "approval_mode": rt.approval_mode.value if hasattr(rt.approval_mode, "value") else str(rt.approval_mode),
            "sla_hours": rt.sla_hours,
        }
        for rt in types
    ]


@router.get("/teams/{team_id}/members")
def list_team_members(
    team_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns members belonging to a specific team."""
    memberships = (
        db.query(TeamMembership)
        .options(joinedload(TeamMembership.user))
        .filter(TeamMembership.team_id == team_id)
        .all()
    )
    return [
        {
            "id": str(m.user.id),
            "name": m.user.name,
            "email": m.user.email,
            "role": m.role.value if hasattr(m.role, "value") else str(m.role),
        }
        for m in memberships
        if m.user
    ]
