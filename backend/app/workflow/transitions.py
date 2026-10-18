from dataclasses import dataclass, field
from typing import Optional, Set
from app.models.user import User
from app.models.team import TeamMembership, TeamRole
from app.models.request import Request, RequestStatus, ApprovalMode


class IllegalTransition(Exception):
    """Raised when a requested status transition violates the workflow state machine (409)."""
    pass


class Forbidden(Exception):
    """Raised when an actor lacks permission or violates separation of duties for a transition (403)."""
    pass


class ValidationError(Exception):
    """Raised when required fields (like reason) are missing for a transition (422)."""
    pass


TERMINAL_STATES = {"done", "cancelled"}
NON_TERMINAL_STATES = {
    "new",
    "triage",
    "awaiting_start_approval",
    "in_progress",
    "awaiting_completion_approval",
}


@dataclass(frozen=True)
class Rule:
    roles: Set[str] = field(default_factory=lambda: {"member", "approver", "lead"})
    actor: Optional[str] = None  # None, "owner", "owner_or_lead"
    needs_owner: bool = False
    needs_priority: bool = False
    mode_in: Optional[Set[str]] = None  # None or set of ApprovalMode values
    not_owner: bool = False  # If True, actor cannot be the request owner
    reason_required: bool = False


# Canonical state machine rules keyed by (from_status, to_status)
TRANSITIONS: dict[tuple[str, str], Rule] = {
    ("new", "triage"): Rule(
        roles={"member", "approver", "lead"},
    ),
    ("triage", "awaiting_start_approval"): Rule(
        roles={"member", "approver", "lead"},
        actor="owner_or_lead",
        needs_owner=True,
        needs_priority=True,
        mode_in={"before", "both"},
    ),
    ("triage", "in_progress"): Rule(
        roles={"member", "approver", "lead"},
        actor="owner_or_lead",
        needs_owner=True,
        needs_priority=True,
        mode_in={"none", "after"},
    ),
    ("awaiting_start_approval", "in_progress"): Rule(
        roles={"approver", "lead"},
        not_owner=True,
    ),
    ("awaiting_start_approval", "triage"): Rule(
        roles={"approver", "lead"},
        not_owner=True,
        reason_required=True,
    ),
    ("in_progress", "awaiting_completion_approval"): Rule(
        roles={"member", "approver", "lead"},
        actor="owner_or_lead",
        mode_in={"after", "both"},
    ),
    ("in_progress", "done"): Rule(
        roles={"member", "approver", "lead"},
        actor="owner_or_lead",
        mode_in={"none", "before"},
    ),
    ("awaiting_completion_approval", "done"): Rule(
        roles={"approver", "lead"},
        not_owner=True,
    ),
    ("awaiting_completion_approval", "in_progress"): Rule(
        roles={"approver", "lead"},
        not_owner=True,
        reason_required=True,
    ),
}


def validate_transition(
    request: Request,
    target_status: str,
    actor_user: User,
    membership: TeamMembership,
    reason: Optional[str] = None,
) -> None:
    """
    Validates whether the transition from request.status to target_status is valid
    according to workflow rules, actor identity, role, and approval mode.
    Raises IllegalTransition (409), Forbidden (403), or ValidationError (422).
    """
    current_status = str(request.status.value if hasattr(request.status, "value") else request.status)
    target = str(target_status.value if hasattr(target_status, "value") else target_status)

    if current_status == target:
        raise IllegalTransition(f"Request is already in '{current_status}' state")

    if current_status in TERMINAL_STATES:
        raise IllegalTransition(f"Cannot transition from terminal state '{current_status}'")

    actor_role = str(membership.role.value if hasattr(membership.role, "value") else membership.role)

    # Special case: cancellation from any non-terminal state
    if target == "cancelled":
        # Reason is always required for cancellation
        if not reason or not reason.strip():
            raise ValidationError("Reason is required to cancel a request")

        # Cancellation allowed by lead, or by creator while status is 'new'
        is_lead = actor_role == "lead"
        is_creator_at_new = current_status == "new" and request.created_by == actor_user.id
        if not (is_lead or is_creator_at_new):
            raise Forbidden("Only a team lead (or the creator while in 'new') can cancel a request")
        return

    rule_key = (current_status, target)
    if rule_key not in TRANSITIONS:
        raise IllegalTransition(f"Invalid state transition from '{current_status}' to '{target}'")

    rule = TRANSITIONS[rule_key]

    # 1. Role check
    if actor_role not in rule.roles:
        raise Forbidden(f"Role '{actor_role}' is not authorized to transition from '{current_status}' to '{target}'")

    # 2. Separation of duties: not_owner
    if rule.not_owner and request.owner_id is not None and request.owner_id == actor_user.id:
        raise Forbidden("Separation of duties: the owner cannot approve or reject their own work")

    # 3. Specific actor constraints
    is_owner = request.owner_id is not None and request.owner_id == actor_user.id
    is_lead = actor_role == "lead"

    if rule.actor == "owner_or_lead":
        if not (is_owner or is_lead):
            raise Forbidden(f"Only the owner or team lead can transition from '{current_status}' to '{target}'")
    elif rule.actor == "owner":
        if not is_owner:
            raise Forbidden(f"Only the owner can transition from '{current_status}' to '{target}'")

    # 4. Guard: needs_owner
    if rule.needs_owner and request.owner_id is None:
        raise IllegalTransition(f"An owner must be assigned before transitioning to '{target}'")

    # 5. Guard: needs_priority
    if rule.needs_priority and request.priority is None:
        raise IllegalTransition(f"Priority must be set before transitioning to '{target}'")

    # 6. Guard: approval mode
    if rule.mode_in is not None:
        approval_mode = str(
            request.request_type.approval_mode.value
            if hasattr(request.request_type.approval_mode, "value")
            else request.request_type.approval_mode
        )
        if approval_mode not in rule.mode_in:
            raise IllegalTransition(
                f"Transition to '{target}' is not allowed for request type with approval mode '{approval_mode}'"
            )

    # 7. Reason required
    if rule.reason_required and (not reason or not reason.strip()):
        raise ValidationError(f"A reason is required when transitioning from '{current_status}' to '{target}'")
