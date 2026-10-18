import concurrent.futures
from starlette.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.team import Team
from app.models.request import RequestType


def test_atomic_claim_concurrency(
    client: TestClient,
    alice_auth_headers: dict[str, str],
    bob_auth_headers: dict[str, str],
    platform_team: Team,
    platform_types: dict[str, RequestType],
):
    """
    Two users attempt to claim the exact same unowned request.
    Database atomic UPDATE ... WHERE owner_id IS NULL guarantees
    that exactly one user succeeds and the other receives a 409 conflict.
    """
    # 1. Create an unowned request in Platform Engineering
    create_res = client.post(
        "/requests",
        headers=alice_auth_headers,
        json={
            "team_id": str(platform_team.id),
            "type_id": str(platform_types["none"].id),
            "title": "Concurrent claim test request",
            "description": "Testing atomic claim behaviour under contention",
            "priority": "medium",
        },
    )
    assert create_res.status_code == 201
    request_id = create_res.json()["id"]

    # 2. Run concurrent claims by Bob and Alice
    results = []

    def try_claim(headers):
        return client.post(f"/requests/{request_id}/claim", headers=headers)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(try_claim, bob_auth_headers)
        f2 = executor.submit(try_claim, alice_auth_headers)
        results = [f1.result(), f2.result()]

    status_codes = sorted([r.status_code for r in results])
    assert status_codes == [200, 409], f"Expected exactly one 200 and one 409, got {status_codes}"

    # Verify conflict details on the 409 response
    conflict_res = next(r for r in results if r.status_code == 409)
    conflict_json = conflict_res.json()
    assert conflict_json["code"] == "ALREADY_CLAIMED"
    assert "already claimed by" in conflict_json["message"].lower()


def test_claim_already_owned_request(
    client: TestClient,
    charlie_auth_headers: dict[str, str],
    bob_auth_headers: dict[str, str],
    platform_team: Team,
    platform_types: dict[str, RequestType],
):
    """Attempting to claim an already owned request returns 409 with current owner information."""
    # 1. Create request
    create_res = client.post(
        "/requests",
        headers=charlie_auth_headers,
        json={
            "team_id": str(platform_team.id),
            "type_id": str(platform_types["none"].id),
            "title": "Already owned claim test",
            "description": "Charlie will claim first, then Bob will attempt to claim.",
        },
    )
    request_id = create_res.json()["id"]

    # 2. Charlie claims it
    claim1 = client.post(f"/requests/{request_id}/claim", headers=charlie_auth_headers)
    assert claim1.status_code == 200
    assert claim1.json()["owner_name"] == "Charlie Member"

    # 3. Bob attempts to claim already owned request
    claim2 = client.post(f"/requests/{request_id}/claim", headers=bob_auth_headers)
    assert claim2.status_code == 409
    body = claim2.json()
    assert body["code"] == "ALREADY_CLAIMED"
    assert "Charlie Member" in body["message"]


def test_claim_by_non_member_returns_404(
    client: TestClient,
    alice_auth_headers: dict[str, str],
    henry_auth_headers: dict[str, str],
    platform_team: Team,
    platform_types: dict[str, RequestType],
):
    """Users outside of the request's team receive 404 to avoid leaking existence."""
    # Alice creates request in Platform Engineering
    create_res = client.post(
        "/requests",
        headers=alice_auth_headers,
        json={
            "team_id": str(platform_team.id),
            "type_id": str(platform_types["none"].id),
            "title": "Platform confidential task",
            "description": "Henry from Customer Ops should not know this exists.",
        },
    )
    request_id = create_res.json()["id"]

    # Henry (non-member) tries to claim
    res = client.post(f"/requests/{request_id}/claim", headers=henry_auth_headers)
    assert res.status_code == 404
