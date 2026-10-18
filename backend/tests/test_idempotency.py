import uuid
from starlette.testclient import TestClient
from app.models.team import Team
from app.models.request import RequestType


def test_idempotent_request_creation_replay(
    client: TestClient,
    alice_auth_headers: dict[str, str],
    platform_team: Team,
    platform_types: dict[str, RequestType],
):
    """
    Submitting the same POST /requests twice with identical payload and Idempotency-Key
    returns the exact same stored response (201) without creating a second record.
    """
    idempotency_key = f"test-key-{uuid.uuid4()}"
    headers = {**alice_auth_headers, "Idempotency-Key": idempotency_key}
    payload = {
        "team_id": str(platform_team.id),
        "type_id": str(platform_types["none"].id),
        "title": "Idempotent creation test",
        "description": "Double submission should produce single entity",
        "priority": "low",
    }

    # First call
    res1 = client.post("/requests", headers=headers, json=payload)
    assert res1.status_code == 201
    body1 = res1.json()

    # Second call (replay)
    res2 = client.post("/requests", headers=headers, json=payload)
    assert res2.status_code == 201
    body2 = res2.json()

    assert body1["id"] == body2["id"]
    assert body1["title"] == body2["title"]
    assert body1["created_at"] == body2["created_at"]


def test_idempotency_key_reused_with_different_payload(
    client: TestClient,
    alice_auth_headers: dict[str, str],
    platform_team: Team,
    platform_types: dict[str, RequestType],
):
    """
    Reusing an Idempotency-Key with a different payload must fail with 422 IDEMPOTENCY_MISMATCH.
    """
    idempotency_key = f"mismatch-key-{uuid.uuid4()}"
    headers = {**alice_auth_headers, "Idempotency-Key": idempotency_key}

    payload1 = {
        "team_id": str(platform_team.id),
        "type_id": str(platform_types["none"].id),
        "title": "Original payload",
        "description": "Payload version 1",
    }
    payload2 = {
        "team_id": str(platform_team.id),
        "type_id": str(platform_types["none"].id),
        "title": "Modified payload",
        "description": "Payload version 2 (different hash)",
    }

    # First submission
    res1 = client.post("/requests", headers=headers, json=payload1)
    assert res1.status_code == 201

    # Second submission with changed payload
    res2 = client.post("/requests", headers=headers, json=payload2)
    assert res2.status_code == 422
    assert res2.json()["code"] == "IDEMPOTENCY_MISMATCH"


def test_idempotent_comment_submission(
    client: TestClient,
    charlie_auth_headers: dict[str, str],
    platform_team: Team,
    platform_types: dict[str, RequestType],
):
    """Submitting a comment twice with the same key creates only one comment."""
    create_res = client.post(
        "/requests",
        headers=charlie_auth_headers,
        json={
            "team_id": str(platform_team.id),
            "type_id": str(platform_types["none"].id),
            "title": "Request for comment idempotency",
        },
    )
    req_id = create_res.json()["id"]

    idemp_key = f"comment-key-{uuid.uuid4()}"
    headers = {**charlie_auth_headers, "Idempotency-Key": idemp_key}
    comment_payload = {"body": "This is an important idempotent comment."}

    # Post comment twice
    c1 = client.post(f"/requests/{req_id}/comments", headers=headers, json=comment_payload)
    assert c1.status_code == 201
    c1_id = c1.json()["id"]

    c2 = client.post(f"/requests/{req_id}/comments", headers=headers, json=comment_payload)
    assert c2.status_code == 201
    c2_id = c2.json()["id"]

    assert c1_id == c2_id

    # Verify only 1 comment exists on the request
    detail = client.get(f"/requests/{req_id}", headers=charlie_auth_headers).json()
    assert len(detail["comments"]) == 1
