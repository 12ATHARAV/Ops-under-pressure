from starlette.testclient import TestClient
from app.models.team import Team
from app.models.request import RequestType


def test_workflow_none_approval_mode(
    client: TestClient,
    charlie_auth_headers: dict[str, str],
    platform_team: Team,
    platform_types: dict[str, RequestType],
):
    """
    ApprovalMode = NONE:
    Flow: new -> triage -> (claim) -> in_progress -> done
    """
    # 1. Create request
    res = client.post(
        "/requests",
        headers=charlie_auth_headers,
        json={
            "team_id": str(platform_team.id),
            "type_id": str(platform_types["none"].id),
            "title": "Pipeline fix without approvals",
            "priority": "low",
        },
    )
    assert res.status_code == 201
    req = res.json()
    req_id = req["id"]
    version = req["version"]

    # 2. new -> triage
    res = client.post(
        f"/requests/{req_id}/transition",
        headers=charlie_auth_headers,
        json={"version": version, "to": "triage"},
    )
    assert res.status_code == 200
    req = res.json()
    version = req["version"]

    # 3. Claim so owner is set
    res = client.post(f"/requests/{req_id}/claim", headers=charlie_auth_headers)
    assert res.status_code == 200
    version = res.json()["version"]

    # 4. triage -> in_progress
    res = client.post(
        f"/requests/{req_id}/transition",
        headers=charlie_auth_headers,
        json={"version": version, "to": "in_progress"},
    )
    assert res.status_code == 200
    version = res.json()["version"]

    # 5. in_progress -> done
    res = client.post(
        f"/requests/{req_id}/transition",
        headers=charlie_auth_headers,
        json={"version": version, "to": "done"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "done"


def test_workflow_before_approval_mode_and_separation_of_duties(
    client: TestClient,
    charlie_auth_headers: dict[str, str],
    bob_auth_headers: dict[str, str],
    platform_team: Team,
    platform_types: dict[str, RequestType],
):
    """
    ApprovalMode = BEFORE:
    Flow: new -> triage -> awaiting_start_approval -> in_progress -> done
    Also verifies:
    - Skipping approval (triage -> in_progress directly) is rejected with 409
    - Approver cannot approve if they are the owner (separation of duties)
    - Rejection requires reason
    """
    # 1. Create request requiring before approval
    res = client.post(
        "/requests",
        headers=charlie_auth_headers,
        json={
            "team_id": str(platform_team.id),
            "type_id": str(platform_types["before"].id),
            "title": "Database migration requiring start approval",
            "priority": "high",
        },
    )
    assert res.status_code == 201
    req_id = res.json()["id"]
    version = res.json()["version"]

    # Charlie claims and moves to triage
    res = client.post(f"/requests/{req_id}/claim", headers=charlie_auth_headers)
    version = res.json()["version"]

    res = client.post(
        f"/requests/{req_id}/transition",
        headers=charlie_auth_headers,
        json={"version": version, "to": "triage"},
    )
    version = res.json()["version"]

    # 2. Try to skip approval by jumping directly from triage to in_progress -> 409
    skip_res = client.post(
        f"/requests/{req_id}/transition",
        headers=charlie_auth_headers,
        json={"version": version, "to": "in_progress"},
    )
    assert skip_res.status_code == 409
    assert skip_res.json()["code"] == "ILLEGAL_TRANSITION"

    # 3. Transition to awaiting_start_approval
    res = client.post(
        f"/requests/{req_id}/transition",
        headers=charlie_auth_headers,
        json={"version": version, "to": "awaiting_start_approval"},
    )
    assert res.status_code == 200
    version = res.json()["version"]

    # 4. Charlie (member) tries to approve -> 403 Forbidden
    member_approve = client.post(
        f"/requests/{req_id}/transition",
        headers=charlie_auth_headers,
        json={"version": version, "to": "in_progress"},
    )
    assert member_approve.status_code == 403

    # 5. Bob (approver) tries to reject without a reason -> 422 Validation Error
    reject_no_reason = client.post(
        f"/requests/{req_id}/transition",
        headers=bob_auth_headers,
        json={"version": version, "to": "triage", "reason": ""},
    )
    assert reject_no_reason.status_code == 422

    # 6. Bob (approver) approves -> in_progress
    approve_res = client.post(
        f"/requests/{req_id}/transition",
        headers=bob_auth_headers,
        json={"version": version, "to": "in_progress", "reason": "Approved start"},
    )
    assert approve_res.status_code == 200
    version = approve_res.json()["version"]

    # 7. Charlie completes work -> done
    done_res = client.post(
        f"/requests/{req_id}/transition",
        headers=charlie_auth_headers,
        json={"version": version, "to": "done"},
    )
    assert done_res.status_code == 200
    assert done_res.json()["status"] == "done"


def test_separation_of_duties_owner_cannot_approve(
    client: TestClient,
    bob_auth_headers: dict[str, str],
    alice_auth_headers: dict[str, str],
    platform_team: Team,
    platform_types: dict[str, RequestType],
):
    """An approver who owns a request cannot approve their own work."""
    # Bob (approver) creates and claims a request
    res = client.post(
        "/requests",
        headers=bob_auth_headers,
        json={
            "team_id": str(platform_team.id),
            "type_id": str(platform_types["before"].id),
            "title": "Bob's self-owned task",
            "priority": "high",
        },
    )
    req_id = res.json()["id"]

    res = client.post(f"/requests/{req_id}/claim", headers=bob_auth_headers)
    version = res.json()["version"]

    res = client.post(
        f"/requests/{req_id}/transition",
        headers=bob_auth_headers,
        json={"version": version, "to": "triage"},
    )
    version = res.json()["version"]

    res = client.post(
        f"/requests/{req_id}/transition",
        headers=bob_auth_headers,
        json={"version": version, "to": "awaiting_start_approval"},
    )
    version = res.json()["version"]

    # Bob attempts to approve his own request -> 403 Forbidden
    self_approve = client.post(
        f"/requests/{req_id}/transition",
        headers=bob_auth_headers,
        json={"version": version, "to": "in_progress"},
    )
    assert self_approve.status_code == 403
    assert "separation of duties" in self_approve.json()["message"].lower()

    # Alice (lead/other approver) CAN approve it
    other_approve = client.post(
        f"/requests/{req_id}/transition",
        headers=alice_auth_headers,
        json={"version": version, "to": "in_progress"},
    )
    assert other_approve.status_code == 200


def test_rejection_moves_back_with_reason(
    client: TestClient,
    charlie_auth_headers: dict[str, str],
    bob_auth_headers: dict[str, str],
    platform_team: Team,
    platform_types: dict[str, RequestType],
):
    """Rejection from awaiting_start_approval requires a reason and moves status back to triage."""
    res = client.post(
        "/requests",
        headers=charlie_auth_headers,
        json={
            "team_id": str(platform_team.id),
            "type_id": str(platform_types["before"].id),
            "title": "Task to be rejected",
        },
    )
    req_id = res.json()["id"]
    res = client.post(f"/requests/{req_id}/claim", headers=charlie_auth_headers)
    version = res.json()["version"]

    res = client.post(
        f"/requests/{req_id}/transition",
        headers=charlie_auth_headers,
        json={"version": version, "to": "triage"},
    )
    version = res.json()["version"]

    res = client.post(
        f"/requests/{req_id}/transition",
        headers=charlie_auth_headers,
        json={"version": version, "to": "awaiting_start_approval"},
    )
    version = res.json()["version"]

    # Bob rejects with reason
    reject_res = client.post(
        f"/requests/{req_id}/transition",
        headers=bob_auth_headers,
        json={"version": version, "to": "triage", "reason": "Missing rollback plan"},
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "triage"
