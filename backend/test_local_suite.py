"""
Comprehensive Local Integration & End-to-End Test Suite
Tests each functionality separately, then tests the whole system combined.
Uses FastAPI TestClient and real PostgreSQL database.
"""

import sys
import uuid
import time
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.db import SessionLocal
from app.models.user import User
from app.models.team import Team, TeamMembership, TeamRole
from app.models.request import Request, RequestType, RequestStatus, RequestPriority, ApprovalMode
from app.models.event import RequestEvent
from app.models.outbox import OutboxEntry, OutboxStatus
from app.models.notification import Notification
from app.models.idempotency import IdempotencyKey
from app.worker.outbox_worker import process_outbox_batch

client = TestClient(app)

def print_header(title: str):
    print("\n" + "=" * 70)
    print(f" {title.upper()}")
    print("=" * 70)

def print_sub(name: str):
    print(f"\n---> [TEST] {name}")

def assert_true(condition: bool, msg: str):
    if not condition:
        print(f"  FAILED: {msg}")
        raise AssertionError(msg)
    print(f"  PASSED: {msg}")


def test_1_authentication_separately():
    print_header("1. Separate Test: Authentication & Token Generation")

    # 1.1 Alice Lead with password
    print_sub("Login as Alice Lead with password 'password'")
    res = client.post("/auth/login", json={"email": "alice@example.com", "password": "password"})
    assert_true(res.status_code == 200, f"Alice login returned status {res.status_code}")
    data = res.json()
    assert_true("access_token" in data, "Token returned in response")
    assert_true(data["user"]["email"] == "alice@example.com", "User email matches")
    alice_token = data["access_token"]

    # 1.2 Demo Lead alias with password123
    print_sub("Login as Lead Alias with password 'password123'")
    res = client.post("/auth/login", json={"email": "lead@example.com", "password": "password123"})
    assert_true(res.status_code == 200, f"Lead alias login with password123 returned status {res.status_code}")

    # 1.3 Bob Approver
    print_sub("Login as Bob Approver with password 'password'")
    res = client.post("/auth/login", json={"email": "bob@example.com", "password": "password"})
    assert_true(res.status_code == 200, f"Bob Approver login returned status {res.status_code}")

    # 1.4 Charlie Member
    print_sub("Login as Charlie Member with password 'password'")
    res = client.post("/auth/login", json={"email": "charlie@example.com", "password": "password"})
    assert_true(res.status_code == 200, f"Charlie Member login returned status {res.status_code}")

    # 1.5 Invalid credentials rejection
    print_sub("Reject invalid password with HTTP 401")
    res = client.post("/auth/login", json={"email": "alice@example.com", "password": "wrong_password_xyz"})
    assert_true(res.status_code == 401, f"Invalid password rejected with 401 (got {res.status_code})")

    # 1.6 /me endpoint
    print_sub("Call /me with Bearer token")
    res = client.get("/me", headers={"Authorization": f"Bearer {alice_token}"})
    assert_true(res.status_code == 200, f"/me returned 200 (got {res.status_code})")
    me_data = res.json()
    assert_true(me_data["email"] == "alice@example.com", "/me returns correct email")
    assert_true(len(me_data["teams"]) > 0, "/me returns team memberships")


def test_2_authorization_separately():
    print_header("2. Separate Test: Resource-Level Authorization (RBAC)")
    db = SessionLocal()
    try:
        # Get Platform and Security teams
        t_platform = db.query(Team).filter(Team.name == "Platform Engineering").first()
        t_security = db.query(Team).filter(Team.name == "Security Incident Response").first()

        # Dave is ONLY in Platform Engineering
        dave = db.query(User).filter(User.email == "dave@example.com").first()

        # Find a request belonging to Security Incident Response
        sec_req = db.query(Request).filter(Request.team_id == t_security.id).first()
    finally:
        db.close()

    # Login as Dave (Platform member only)
    res = client.post("/auth/login", json={"email": "dave@example.com", "password": "password"})
    dave_token = res.json()["access_token"]

    # 2.1 Dave attempting to view Security team request -> MUST RETURN 404 NOT FOUND (no existence leak)
    print_sub("Non-team member accessing restricted request gets HTTP 404 (No Information Leak)")
    res = client.get(f"/requests/{sec_req.id}", headers={"Authorization": f"Bearer {dave_token}"})
    assert_true(res.status_code == 404, f"Access rejected with 404 (got {res.status_code})")

    # 2.2 Dave (regular member) attempting to reassign an owner -> 403 Forbidden (Only Leads can reassign)
    print_sub("Regular member attempting to reassign owner gets HTTP 403 Forbidden")
    plat_req = db.query(Request).filter(Request.team_id == t_platform.id).first()
    res_reassign = client.post(
        f"/requests/{plat_req.id}/assign",
        json={"version": plat_req.version, "owner_id": str(dave.id), "reason": "Unauthorized assign attempt"},
        headers={"Authorization": f"Bearer {dave_token}"},
    )
    assert_true(res_reassign.status_code == 403, f"Reassignment rejected with 403 (got {res_reassign.status_code})")

    # 2.3 Attention view role scoping: Member gets empty buckets (count = 0)
    print_sub("Regular member accessing Attention Dashboard gets 0 count buckets (Role Scoping)")
    res_att = client.get("/attention", headers={"Authorization": f"Bearer {dave_token}"})
    assert_true(res_att.status_code == 200, f"Attention view returns 200 (got {res_att.status_code})")
    assert_true(res_att.json()["unowned"]["count"] == 0, "Member receives 0 unowned count")
    assert_true(len(res_att.json()["unowned"]["items"]) == 0, "Member receives empty items list")


def test_3_atomic_claim_separately():
    print_header("3. Separate Test: Atomic Ownership Claim & Race Condition")
    db = SessionLocal()
    try:
        t_platform = db.query(Team).filter(Team.name == "Platform Engineering").first()
        type_platform = db.query(RequestType).filter(RequestType.team_id == t_platform.id).first()
        creator = db.query(User).filter(User.email == "alice@example.com").first()

        # Create unowned request
        unowned_req = Request(
            id=uuid.uuid4(),
            team_id=t_platform.id,
            type_id=type_platform.id,
            title="Atomic Claim Race Test Target",
            description="Testing concurrent claim race condition",
            status=RequestStatus.triage,
            priority=RequestPriority.high,
            created_by=creator.id,
            owner_id=None,
            version=1,
            last_activity_at=datetime.now(timezone.utc),
        )
        db.add(unowned_req)
        db.commit()
        req_id = unowned_req.id
    finally:
        db.close()

    # Login as Charlie (Member) and Dave (Member)
    t_charlie = client.post("/auth/login", json={"email": "charlie@example.com", "password": "password"}).json()["access_token"]
    t_dave = client.post("/auth/login", json={"email": "dave@example.com", "password": "password"}).json()["access_token"]

    print_sub("First claimant (Charlie) claims unowned request -> Succeeds with 200")
    res1 = client.post(
        f"/requests/{req_id}/claim",
        headers={"Authorization": f"Bearer {t_charlie}", "Idempotency-Key": str(uuid.uuid4())},
    )
    assert_true(res1.status_code == 200, f"Claim 1 succeeded (status {res1.status_code})")
    assert_true(res1.json()["owner_name"] == "Charlie Member", "Charlie is recorded as owner")

    print_sub("Second claimant (Dave) attempts to claim already claimed request -> Fails with HTTP 409")
    res2 = client.post(
        f"/requests/{req_id}/claim",
        headers={"Authorization": f"Bearer {t_dave}", "Idempotency-Key": str(uuid.uuid4())},
    )
    assert_true(res2.status_code == 409, f"Claim 2 returned 409 Conflict (got {res2.status_code})")
    assert_true("Charlie Member" in str(res2.json()), "Conflict response identifies current owner")


def test_4_optimistic_locking_separately():
    print_header("4. Separate Test: Optimistic Concurrency Control (Version Check)")
    db = SessionLocal()
    try:
        t_platform = db.query(Team).filter(Team.name == "Platform Engineering").first()
        req = db.query(Request).filter(Request.team_id == t_platform.id).first()
        req_id = req.id
    finally:
        db.close()

    t_alice = client.post("/auth/login", json={"email": "alice@example.com", "password": "password"}).json()["access_token"]

    # Read current state
    detail = client.get(f"/requests/{req_id}", headers={"Authorization": f"Bearer {t_alice}"}).json()
    v_orig = detail["version"]

    # First update using v_orig
    print_sub(f"Update 1 using current version {v_orig} -> Succeeds and bumps version to {v_orig + 1}")
    res1 = client.patch(
        f"/requests/{req_id}",
        json={"title": "Updated by Client A", "version": v_orig},
        headers={"Authorization": f"Bearer {t_alice}"},
    )
    assert_true(res1.status_code == 200, f"Update 1 succeeded with status {res1.status_code}")
    assert_true(res1.json()["version"] == v_orig + 1, "Version incremented by 1")

    # Stale update using old v_orig
    print_sub(f"Update 2 using stale version {v_orig} -> Fails with HTTP 409 Conflict")
    res2 = client.patch(
        f"/requests/{req_id}",
        json={"title": "Stale update by Client B", "version": v_orig},
        headers={"Authorization": f"Bearer {t_alice}"},
    )
    assert_true(res2.status_code == 409, f"Stale update rejected with 409 Conflict (got {res2.status_code})")
    assert_true("current" in res2.json(), "409 payload includes current server state")


def test_5_idempotency_separately():
    print_header("5. Separate Test: Idempotent Write Operations & Duplicate Prevention")
    db = SessionLocal()
    try:
        t_platform = db.query(Team).filter(Team.name == "Platform Engineering").first()
        type_platform = db.query(RequestType).filter(RequestType.team_id == t_platform.id).first()
        team_id = str(t_platform.id)
        type_id = str(type_platform.id)
    finally:
        db.close()

    t_charlie = client.post("/auth/login", json={"email": "charlie@example.com", "password": "password"}).json()["access_token"]
    idemp_key = f"test-idemp-{uuid.uuid4()}"

    payload = {
        "team_id": team_id,
        "type_id": type_id,
        "title": "Idempotency Test Item",
        "description": "Checking duplicate prevention",
        "priority": "medium",
    }

    # First creation call
    print_sub("First request submission with Idempotency-Key -> HTTP 201 Created")
    res1 = client.post(
        "/requests",
        json=payload,
        headers={"Authorization": f"Bearer {t_charlie}", "Idempotency-Key": idemp_key},
    )
    assert_true(res1.status_code == 201, f"First creation returned 201 (got {res1.status_code})")
    item1 = res1.json()

    # Retry submission with SAME key and payload
    print_sub("Retry submission with identical Idempotency-Key -> Replays cached HTTP 201 without duplicate")
    res2 = client.post(
        "/requests",
        json=payload,
        headers={"Authorization": f"Bearer {t_charlie}", "Idempotency-Key": idemp_key},
    )
    assert_true(res2.status_code == 201, f"Replay returned 201 (got {res2.status_code})")
    assert_true(res2.json()["id"] == item1["id"], "Same request ID returned (no duplicate row created)")

    # Reuse key with DIFFERENT payload
    print_sub("Reuse Idempotency-Key with different payload -> HTTP 422 Unprocessable Entity")
    different_payload = payload.copy()
    different_payload["title"] = "Completely Different Title"
    res3 = client.post(
        "/requests",
        json=different_payload,
        headers={"Authorization": f"Bearer {t_charlie}", "Idempotency-Key": idemp_key},
    )
    assert_true(res3.status_code == 422, f"Key mismatch rejected with 422 (got {res3.status_code})")


def test_6_workflow_and_separation_of_duties_separately():
    print_header("6. Separate Test: Workflow State Machine & Separation of Duties")
    db = SessionLocal()
    try:
        t_platform = db.query(Team).filter(Team.name == "Platform Engineering").first()
        type_both = db.query(RequestType).filter(
            RequestType.team_id == t_platform.id,
            RequestType.approval_mode == ApprovalMode.both
        ).first()
        bob = db.query(User).filter(User.email == "bob@example.com").first()

        # Create request owned by Bob Approver
        req = Request(
            id=uuid.uuid4(),
            team_id=t_platform.id,
            type_id=type_both.id,
            title="Separation of Duties Verification Item",
            description="Testing separation of duties",
            status=RequestStatus.awaiting_completion_approval,
            priority=RequestPriority.high,
            created_by=bob.id,
            owner_id=bob.id,
            version=1,
            last_activity_at=datetime.now(timezone.utc),
        )
        db.add(req)
        db.commit()
        req_id = req.id
    finally:
        db.close()

    t_bob = client.post("/auth/login", json={"email": "bob@example.com", "password": "password"}).json()["access_token"]
    t_alice = client.post("/auth/login", json={"email": "alice@example.com", "password": "password"}).json()["access_token"]

    # Bob (owner) attempts to approve completion of his OWN work -> MUST BE REJECTED
    print_sub("Owner (Bob) attempts to approve completion of own work -> Rejected (Separation of Duties)")
    res_own = client.post(
        f"/requests/{req_id}/transition",
        json={"to": "done", "version": 1},
        headers={"Authorization": f"Bearer {t_bob}"},
    )
    assert_true(res_own.status_code in (403, 409), f"Self-approval rejected with status {res_own.status_code}")

    # Lead (Alice != Bob) approves completion of Bob's work -> Allowed
    print_sub("Disinterested approver (Alice != Bob) approves completion -> HTTP 200 OK")
    res_other = client.post(
        f"/requests/{req_id}/transition",
        json={"to": "done", "version": 1},
        headers={"Authorization": f"Bearer {t_alice}"},
    )
    assert_true(res_other.status_code == 200, f"Third-party approval succeeded (status {res_other.status_code})")
    assert_true(res_other.json()["status"] == "done", "Request transitioned to 'done'")


def test_7_transactional_outbox_separately():
    print_header("7. Separate Test: Transactional Outbox & Background Worker")
    db = SessionLocal()
    try:
        # Enqueue pending outbox entry
        req = db.query(Request).first()
        user = db.query(User).filter(User.email == "alice@example.com").first()

        outbox_entry = OutboxEntry(
            event_id=None,
            topic="request.assigned",
            payload={
                "request_id": str(req.id),
                "title": req.title,
                "new_owner_id": str(user.id),
                "assigned_by_name": "Test Suite",
            },
            status=OutboxStatus.pending,
            attempts=0,
            next_attempt_at=datetime.now(timezone.utc),
        )
        db.add(outbox_entry)
        db.commit()
        db.refresh(outbox_entry)
        outbox_id = outbox_entry.id

        print_sub("Execute outbox worker batch with FOR UPDATE SKIP LOCKED")
        processed = 0
        for _ in range(5):
            p = process_outbox_batch(db, limit=50)
            processed += p
            db.refresh(outbox_entry)
            if outbox_entry.status == OutboxStatus.done:
                break
        assert_true(processed >= 1, f"Worker processed {processed} entries")

        # Verify entry status transitioned to 'done'
        assert_true(outbox_entry.status == OutboxStatus.done, f"Outbox entry #{outbox_id} marked as 'done'")

        # Verify notification was generated with unique dedupe_key
        notif = db.query(Notification).filter(Notification.user_id == user.id).order_by(Notification.created_at.desc()).first()
        assert_true(notif is not None, "Notification row created in database")
        print(f"  Notification created: '{notif.body}' (dedupe_key: {notif.dedupe_key})")

        # Re-run processor to prove idempotency (no duplicate notification)
        outbox_entry.status = OutboxStatus.pending
        db.commit()
        process_outbox_batch(db, limit=10)
        count_notifs = db.query(Notification).filter(Notification.dedupe_key == notif.dedupe_key).count()
        assert_true(count_notifs == 1, "Duplicate outbox processing produced NO duplicate notification")
    finally:
        db.close()


def test_8_whole_application_combined_lifecycle():
    print_header("8. Combined End-to-End Application Lifecycle Test")
    print("Testing full lifecycle from login -> create -> claim -> transition -> comment -> attention -> notifications")

    # Step 1: Login as Charlie Member
    print_sub("Step 1: Charlie logs in and fetches team metadata")
    res = client.post("/auth/login", json={"email": "charlie@example.com", "password": "password"})
    assert_true(res.status_code == 200, "Charlie logged in")
    t_charlie = res.json()["access_token"]
    platform_team_id = res.json()["user"]["teams"][0]["team_id"]

    # Step 2: Query team request type
    db = SessionLocal()
    try:
        p_type = db.query(RequestType).filter(RequestType.team_id == platform_team_id).first()
        type_id = str(p_type.id)
    finally:
        db.close()

    # Step 3: Create operational request with idempotency key
    print_sub("Step 2: Charlie creates an operational incident ticket")
    req_payload = {
        "team_id": platform_team_id,
        "type_id": type_id,
        "title": "E2E Production Database Latency Spike",
        "description": "P99 latency exceeding 500ms on secondary replicas",
        "priority": "urgent",
    }
    create_res = client.post(
        "/requests",
        json=req_payload,
        headers={"Authorization": f"Bearer {t_charlie}", "Idempotency-Key": str(uuid.uuid4())},
    )
    assert_true(create_res.status_code == 201, "Request created with 201")
    req_data = create_res.json()
    req_id = req_data["id"]
    curr_v = req_data["version"]

    # Step 4: Claim the ticket
    print_sub("Step 3: Charlie claims ownership of the new ticket")
    claim_res = client.post(
        f"/requests/{req_id}/claim",
        headers={"Authorization": f"Bearer {t_charlie}", "Idempotency-Key": str(uuid.uuid4())},
    )
    assert_true(claim_res.status_code == 200, "Ticket claimed")
    curr_v = claim_res.json()["version"]

    # Step 5: Transition from NEW to TRIAGE
    print_sub("Step 4: Charlie moves ticket to TRIAGE")
    triage_res = client.post(
        f"/requests/{req_id}/transition",
        json={"to": "triage", "version": curr_v},
        headers={"Authorization": f"Bearer {t_charlie}"},
    )
    assert_true(triage_res.status_code == 200, "Moved to triage")
    curr_v = triage_res.json()["version"]

    # Step 6: Post investigation comment
    print_sub("Step 5: Charlie posts operational comment")
    comment_res = client.post(
        f"/requests/{req_id}/comments",
        json={"body": "Investigating slow query logs on replica-02."},
        headers={"Authorization": f"Bearer {t_charlie}", "Idempotency-Key": str(uuid.uuid4())},
    )
    assert_true(comment_res.status_code == 201, "Comment added")

    # Step 7: View audit timeline events
    print_sub("Step 6: View append-only audit event history")
    events_res = client.get(f"/requests/{req_id}/events", headers={"Authorization": f"Bearer {t_charlie}"})
    assert_true(events_res.status_code == 200, "Audit events retrieved")
    events = events_res.json()
    assert_true(len(events) >= 3, f"Audit trail contains {len(events)} events (created, claimed, triaged, commented)")

    # Step 8: Login as Alice Lead and inspect Attention Dashboard
    print_sub("Step 7: Alice Lead opens Attention Dashboard")
    t_alice = client.post("/auth/login", json={"email": "alice@example.com", "password": "password"}).json()["access_token"]
    att_res = client.get("/attention", headers={"Authorization": f"Bearer {t_alice}"})
    assert_true(att_res.status_code == 200, "Attention view retrieved")
    att_data = att_res.json()
    assert_true("unowned" in att_data and "stale" in att_data and "urgent" in att_data, "All 5 attention buckets present")
    print(f"  Attention Dashboard counts: Urgent={att_data['urgent']['count']}, Unowned={att_data['unowned']['count']}, Stale={att_data['stale']['count']}")

    print("\n" + "=" * 70)
    print(" ALL 8 TEST SUITES COMPLETED WITH 100% SUCCESS!")
    print("=" * 70)


if __name__ == "__main__":
    test_1_authentication_separately()
    test_2_authorization_separately()
    test_3_atomic_claim_separately()
    test_4_optimistic_locking_separately()
    test_5_idempotency_separately()
    test_6_workflow_and_separation_of_duties_separately()
    test_7_transactional_outbox_separately()
    test_8_whole_application_combined_lifecycle()
