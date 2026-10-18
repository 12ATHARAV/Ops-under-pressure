from starlette.testclient import TestClient
from app.models.team import Team
from app.models.request import RequestType
from app.models.user import User


def test_member_cannot_reassign_owner(
    client: TestClient,
    charlie_auth_headers: dict[str, str],
    alice_auth_headers: dict[str, str],
    platform_team: Team,
    platform_types: dict[str, RequestType],
    db_session,
):
    """Only a team lead can reassign owners. A member gets 403 Forbidden."""
    create_res = client.post(
        "/requests",
        headers=charlie_auth_headers,
        json={
            "team_id": str(platform_team.id),
            "type_id": str(platform_types["none"].id),
            "title": "Task for reassignment test",
        },
    )
    req_id = create_res.json()["id"]
    version = create_res.json()["version"]

    bob = db_session.query(User).filter(User.email == "bob@example.com").first()

    # Charlie (member) attempts to reassign to Bob -> 403
    fail_res = client.post(
        f"/requests/{req_id}/assign",
        headers=charlie_auth_headers,
        json={"version": version, "owner_id": str(bob.id), "reason": "Charlie trying to assign"},
    )
    assert fail_res.status_code == 403

    # Alice (lead) can reassign -> 200
    ok_res = client.post(
        f"/requests/{req_id}/assign",
        headers=alice_auth_headers,
        json={"version": version, "owner_id": str(bob.id), "reason": "Alice assigning to Bob"},
    )
    assert ok_res.status_code == 200
    assert ok_res.json()["owner_name"] == "Bob Approver"


def test_non_member_receives_404_for_team_request(
    client: TestClient,
    alice_auth_headers: dict[str, str],
    henry_auth_headers: dict[str, str],
    platform_team: Team,
    platform_types: dict[str, RequestType],
):
    """
    If a user is not a member of a team, attempting to view, edit, or transition
    a request in that team returns 404 NOT FOUND (no leak of resource existence).
    """
    create_res = client.post(
        "/requests",
        headers=alice_auth_headers,
        json={
            "team_id": str(platform_team.id),
            "type_id": str(platform_types["none"].id),
            "title": "Confidential platform operational item",
        },
    )
    req_id = create_res.json()["id"]

    # Henry is in Customer Operations only, not Platform Engineering
    view_res = client.get(f"/requests/{req_id}", headers=henry_auth_headers)
    assert view_res.status_code == 404

    edit_res = client.patch(
        f"/requests/{req_id}",
        headers=henry_auth_headers,
        json={"version": 1, "title": "Hacked title"},
    )
    assert edit_res.status_code == 404


def test_attention_view_role_scoping(
    client: TestClient,
    charlie_auth_headers: dict[str, str],
    alice_auth_headers: dict[str, str],
):
    """
    The Attention view returns counts only for teams where the user is lead.
    Charlie (member in Platform) gets empty/0 buckets.
    Alice (lead in Platform) gets populated buckets.
    """
    # Charlie view
    charlie_res = client.get("/attention", headers=charlie_auth_headers)
    assert charlie_res.status_code == 200
    c_data = charlie_res.json()
    assert c_data["unowned"]["count"] == 0
    assert len(c_data["unowned"]["items"]) == 0

    # Alice view
    alice_res = client.get("/attention", headers=alice_auth_headers)
    assert alice_res.status_code == 200
    a_data = alice_res.json()
    assert "unowned" in a_data
    assert "stale" in a_data
    assert "overdue" in a_data
    assert "stuck_approval" in a_data
    assert "urgent" in a_data
