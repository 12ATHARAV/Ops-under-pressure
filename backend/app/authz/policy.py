from typing import Any, Callable
from app.models.user import User
from app.models.team import TeamRole, TeamMembership
from app.models.request import Request


class AuthorizationError(Exception):
    """Base authorization error."""
    pass


class NotFoundError(Exception):
    """Resource not found or caller not in the resource's team (no existence leak)."""
    pass


class ForbiddenError(Exception):
    """User does not have permission to perform this action."""
    pass


# Policy checks given (role: TeamRole, user: User, request: Request | None)
POLICY: dict[str, Callable[[TeamRole, User, Request | None], bool]] = {
    "view": lambda role, user, req: role in {TeamRole.member, TeamRole.approver, TeamRole.lead},
    "create": lambda role, user, req: role in {TeamRole.member, TeamRole.approver, TeamRole.lead},
    "claim": lambda role, user, req: (
        role in {TeamRole.member, TeamRole.approver, TeamRole.lead}
        and (req is None or req.owner_id is None)
    ),
    "edit": lambda role, user, req: (
        req is not None
        and (role == TeamRole.lead or (req.owner_id is not None and req.owner_id == user.id))
    ),
    "assign": lambda role, user, req: role == TeamRole.lead,
    "cancel": lambda role, user, req: (
        role == TeamRole.lead
        or (req is not None and req.status == "new" and req.created_by == user.id)
    ),
    "approve": lambda role, user, req: (
        role in {TeamRole.approver, TeamRole.lead}
        and (req is None or req.owner_id != user.id)
    ),
    "reject": lambda role, user, req: (
        role in {TeamRole.approver, TeamRole.lead}
        and (req is None or req.owner_id != user.id)
    ),
    "view_attention": lambda role, user, req: role == TeamRole.lead,
    "comment": lambda role, user, req: role in {TeamRole.member, TeamRole.approver, TeamRole.lead},
}


def authorize(user: User, request: Request, action: str) -> TeamMembership:
    """
    Authorizes a user action on a given request.
    Raises NotFoundError if the user is not a member of the request's team (no existence leak).
    Raises ForbiddenError if user's role/identity does not permit the action.
    """
    # Locate user membership in request's team
    membership = next((m for m in user.memberships if m.team_id == request.team_id), None)
    if membership is None:
        raise NotFoundError(f"Request {request.id} not found")

    check_fn = POLICY.get(action)
    if not check_fn:
        raise ForbiddenError(f"Unknown action: {action}")

    # Enforce separation of duties: approver cannot be owner
    if action in {"approve", "reject"} and request.owner_id == user.id:
        raise ForbiddenError("Approver cannot be the owner of the request (separation of duties)")

    if not check_fn(membership.role, user, request):
        raise ForbiddenError(f"User role '{membership.role}' does not have permission to {action}")

    return membership
