from uuid import UUID
from typing import Callable
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.auth.deps import get_current_user
from app.models.user import User
from app.models.team import TeamMembership
from app.authz.policy import POLICY, ForbiddenError, NotFoundError


def get_membership(user: User, team_id: UUID, db: Session) -> TeamMembership:
    """Helper to fetch membership or return 404 so team resources aren't leaked to non-members."""
    membership = (
        db.query(TeamMembership)
        .filter(TeamMembership.user_id == user.id, TeamMembership.team_id == team_id)
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found or access denied",
        )
    return membership


def require_team_role(min_role: str) -> Callable:
    """Dependency factory checking that the user has at least a specific role in a team."""
    def dependency(
        team_id: UUID,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> TeamMembership:
        m = get_membership(current_user, team_id, db)
        role_hierarchy = {"member": 1, "approver": 2, "lead": 3}
        if role_hierarchy.get(str(m.role.value), 0) < role_hierarchy.get(min_role, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action requires at least '{min_role}' role in this team",
            )
        return m

    return dependency
