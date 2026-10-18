import uuid
import random
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db import SessionLocal, engine, Base
from app.auth.security import hash_password
from app.models.user import User
from app.models.team import Team, TeamMembership, TeamRole
from app.models.request import (
    Request,
    RequestType,
    Comment,
    ApprovalMode,
    RequestStatus,
    RequestPriority,
)
from app.models.event import RequestEvent
from app.models.outbox import OutboxEntry, OutboxStatus
from app.models.notification import Notification
from app.models.idempotency import IdempotencyKey


def seed_database() -> None:
    session: Session = SessionLocal()
    try:
        print("Starting database seed...")

        # Clear existing data in reverse dependency order
        session.query(Notification).delete()
        session.query(OutboxEntry).delete()
        session.query(IdempotencyKey).delete()
        session.query(Comment).delete()
        session.query(RequestEvent).delete()
        session.query(Request).delete()
        session.query(RequestType).delete()
        session.query(TeamMembership).delete()
        session.query(Team).delete()
        session.query(User).delete()
        session.commit()
        print("Cleared existing data.")

        now = datetime.now(timezone.utc)
        default_pwd_hash = hash_password("Newtonite2026!Ops")

        # 1. Create Users
        users_data = [
            ("alice@example.com", "Alice Lead"),
            ("bob@example.com", "Bob Approver"),
            ("charlie@example.com", "Charlie Member"),
            ("dave@example.com", "Dave Member"),
            ("emma@example.com", "Emma Lead"),
            ("frank@example.com", "Frank Approver"),
            ("grace@example.com", "Grace Member"),
            ("henry@example.com", "Henry Member"),
            ("iris@example.com", "Iris Lead"),
            ("jack@example.com", "Jack Approver"),
            ("kate@example.com", "Kate Member"),
            ("leo@example.com", "Leo Member"),
            ("lead@example.com", "Demo Lead"),
            ("approver@example.com", "Demo Approver"),
            ("member@example.com", "Demo Member"),
        ]

        users: dict[str, User] = {}
        for email, name in users_data:
            user = User(
                id=uuid.uuid4(),
                email=email,
                name=name,
                password_hash=default_pwd_hash,
                created_at=now - timedelta(days=30),
            )
            session.add(user)
            users[email] = user
        session.flush()
        print(f"Created {len(users)} users.")

        # 2. Create Teams
        team_platform = Team(id=uuid.uuid4(), name="Platform Engineering")
        team_customer = Team(id=uuid.uuid4(), name="Customer Operations")
        team_security = Team(id=uuid.uuid4(), name="Security Incident Response")

        teams = [team_platform, team_customer, team_security]
        session.add_all(teams)
        session.flush()
        print("Created 3 teams.")

        # 3. Create Team Memberships
        memberships_data = [
            # Platform Engineering
            (users["alice@example.com"], team_platform, TeamRole.lead),
            (users["bob@example.com"], team_platform, TeamRole.approver),
            (users["charlie@example.com"], team_platform, TeamRole.member),
            (users["dave@example.com"], team_platform, TeamRole.member),
            (users["emma@example.com"], team_platform, TeamRole.member),
            (users["iris@example.com"], team_platform, TeamRole.member),
            (users["lead@example.com"], team_platform, TeamRole.lead),
            (users["approver@example.com"], team_platform, TeamRole.approver),
            (users["member@example.com"], team_platform, TeamRole.member),
            # Customer Operations
            (users["emma@example.com"], team_customer, TeamRole.lead),
            (users["frank@example.com"], team_customer, TeamRole.approver),
            (users["grace@example.com"], team_customer, TeamRole.member),
            (users["henry@example.com"], team_customer, TeamRole.member),
            (users["bob@example.com"], team_customer, TeamRole.member),
            (users["jack@example.com"], team_customer, TeamRole.approver),
            # Security Incident Response
            (users["iris@example.com"], team_security, TeamRole.lead),
            (users["jack@example.com"], team_security, TeamRole.approver),
            (users["alice@example.com"], team_security, TeamRole.approver),
            (users["kate@example.com"], team_security, TeamRole.member),
            (users["leo@example.com"], team_security, TeamRole.member),
        ]

        for user, team, role in memberships_data:
            m = TeamMembership(user_id=user.id, team_id=team.id, role=role)
            session.add(m)
        session.flush()
        print("Created team memberships.")

        # 4. Create Request Types with varied approval modes
        types_data = [
            # Platform Engineering
            (team_platform, "Infrastructure Provisioning", ApprovalMode.both, 24),
            (team_platform, "Database Migration", ApprovalMode.before, 12),
            (team_platform, "CI/CD Pipeline Fix", ApprovalMode.none, 8),
            (team_platform, "Cloud Resource Scaling", ApprovalMode.after, 48),
            # Customer Operations
            (team_customer, "VIP Account Recovery", ApprovalMode.before, 4),
            (team_customer, "Data Export Request", ApprovalMode.both, 72),
            (team_customer, "Billing Dispute Investigation", ApprovalMode.after, 24),
            (team_customer, "General Service Inquiry", ApprovalMode.none, 16),
            # Security Incident Response
            (team_security, "Critical Vulnerability Patch", ApprovalMode.before, 6),
            (team_security, "Access Revocation", ApprovalMode.none, 2),
            (team_security, "Security Audit Request", ApprovalMode.both, 96),
            (team_security, "Suspicious Activity Investigation", ApprovalMode.after, 12),
        ]

        types_by_team: dict[uuid.UUID, list[RequestType]] = {
            team_platform.id: [],
            team_customer.id: [],
            team_security.id: [],
        }

        for team, name, mode, sla in types_data:
            rt = RequestType(
                id=uuid.uuid4(),
                team_id=team.id,
                name=name,
                approval_mode=mode,
                sla_hours=sla,
            )
            session.add(rt)
            types_by_team[team.id].append(rt)
        session.flush()
        print("Created request types.")

        # 5. Create 200+ Requests with rich history, comments, and varied statuses
        team_members_map: dict[uuid.UUID, list[User]] = {
            team_platform.id: [users["alice@example.com"], users["bob@example.com"], users["charlie@example.com"], users["dave@example.com"]],
            team_customer.id: [users["emma@example.com"], users["frank@example.com"], users["grace@example.com"], users["henry@example.com"]],
            team_security.id: [users["iris@example.com"], users["jack@example.com"], users["kate@example.com"], users["leo@example.com"]],
        }

        titles_pool = [
            "Upgrade Postgres cluster to version 16 in staging",
            "Investigate latency spike on payment gateway API",
            "Provision isolated VPC for data science sandbox",
            "Emergency certificate rotation for auth.company.internal",
            "Customer enterprise tenant bulk data migration",
            "Resolve webhook delivery failure to partner endpoint",
            "Audit IAM permissions on production S3 buckets",
            "Mitigate DDoS attempt targeting edge routers",
            "Scale Kubernetes worker nodes ahead of product launch",
            "Investigate suspicious login from unrecognized IP CIDR",
            "Patch OpenSSL CVE-2024 vulnerability across bastion hosts",
            "Restore deleted database backup snapshot for audit compliance",
            "Implement rate limiting on external partner public API",
            "Deploy hotfix for high-priority memory leak in worker daemon",
            "Investigate broken Prometheus alerting pipeline in US-East",
            "Configure Terraform state locking on remote backend",
            "Rotate KMS keys for sensitive customer PII tables",
            "Triage zero-day disclosure advisory from vendor",
            "Resolve cross-region replication lag on search index",
            "Investigate intermittent 502 Bad Gateway responses",
        ]

        statuses = [
            RequestStatus.new,
            RequestStatus.triage,
            RequestStatus.awaiting_start_approval,
            RequestStatus.in_progress,
            RequestStatus.awaiting_completion_approval,
            RequestStatus.done,
            RequestStatus.cancelled,
        ]

        priorities = [
            RequestPriority.low,
            RequestPriority.medium,
            RequestPriority.high,
            RequestPriority.urgent,
        ]

        random.seed(42)  # Deterministic seed data
        requests_created = 0

        # Create distinct attention items explicitly first:
        # a) Unowned items older than 4 hours
        for i in range(12):
            team = teams[i % 3]
            rt = types_by_team[team.id][i % len(types_by_team[team.id])]
            creator = team_members_map[team.id][0]
            created_at = now - timedelta(hours=random.randint(5, 48))
            req = Request(
                id=uuid.uuid4(),
                team_id=team.id,
                type_id=rt.id,
                title=f"[Attention: Unowned] {titles_pool[i % len(titles_pool)]} #{i+1}",
                description=f"Operational request awaiting ownership assignment and triage in {team.name}.",
                status=RequestStatus.new if i % 2 == 0 else RequestStatus.triage,
                priority=RequestPriority.high if i % 3 == 0 else RequestPriority.medium,
                owner_id=None,
                created_by=creator.id,
                version=1,
                due_at=created_at + timedelta(hours=rt.sla_hours or 24),
                last_activity_at=created_at,
                created_at=created_at,
                updated_at=created_at,
            )
            session.add(req)
            session.flush()
            event = RequestEvent(
                request_id=req.id,
                actor_id=creator.id,
                type="created",
                from_value=None,
                to_value={"title": req.title, "status": "new", "priority": req.priority.value},
                reason="Unowned request created",
                created_at=created_at,
            )
            session.add(event)
            requests_created += 1

        # b) Active Stale items (last_activity_at > 24 hours ago)
        for i in range(15):
            team = teams[i % 3]
            rt = types_by_team[team.id][i % len(types_by_team[team.id])]
            members = team_members_map[team.id]
            creator, owner = members[0], members[1]
            created_at = now - timedelta(days=random.randint(3, 10))
            last_activity = now - timedelta(hours=random.randint(26, 72))
            req = Request(
                id=uuid.uuid4(),
                team_id=team.id,
                type_id=rt.id,
                title=f"[Attention: Stale] {titles_pool[(i+3) % len(titles_pool)]} #{i+1}",
                description=f"Active work item with no progress logged in the past 24+ hours.",
                status=RequestStatus.in_progress,
                priority=RequestPriority.medium,
                owner_id=owner.id,
                created_by=creator.id,
                version=2,
                due_at=now + timedelta(hours=24),
                last_activity_at=last_activity,
                created_at=created_at,
                updated_at=last_activity,
            )
            session.add(req)
            session.flush()
            session.add(RequestEvent(
                request_id=req.id,
                actor_id=creator.id,
                type="created",
                to_value={"title": req.title, "status": "new"},
                created_at=created_at,
            ))
            session.add(RequestEvent(
                request_id=req.id,
                actor_id=owner.id,
                type="owner_changed",
                to_value={"owner_id": str(owner.id), "owner_name": owner.name},
                created_at=last_activity,
            ))
            requests_created += 1

        # c) Overdue items (due_at < now)
        for i in range(15):
            team = teams[i % 3]
            rt = types_by_team[team.id][i % len(types_by_team[team.id])]
            members = team_members_map[team.id]
            creator, owner = members[0], members[2]
            created_at = now - timedelta(days=5)
            due_at = now - timedelta(hours=random.randint(2, 36))
            req = Request(
                id=uuid.uuid4(),
                team_id=team.id,
                type_id=rt.id,
                title=f"[Attention: Overdue] {titles_pool[(i+6) % len(titles_pool)]} #{i+1}",
                description="High priority request that has surpassed its target SLA completion window.",
                status=RequestStatus.in_progress,
                priority=RequestPriority.high,
                owner_id=owner.id,
                created_by=creator.id,
                version=2,
                due_at=due_at,
                last_activity_at=now - timedelta(hours=3),
                created_at=created_at,
                updated_at=now - timedelta(hours=3),
            )
            session.add(req)
            session.flush()
            session.add(RequestEvent(
                request_id=req.id,
                actor_id=creator.id,
                type="created",
                to_value={"title": req.title, "status": "new"},
                created_at=created_at,
            ))
            requests_created += 1

        # d) Stuck in approval (> 8 hours)
        for i in range(12):
            team = teams[i % 3]
            # Use request types with before or both
            rt = [t for t in types_by_team[team.id] if t.approval_mode in (ApprovalMode.before, ApprovalMode.both)][0]
            members = team_members_map[team.id]
            creator, owner = members[0], members[3]
            created_at = now - timedelta(days=2)
            stuck_since = now - timedelta(hours=random.randint(10, 48))
            req = Request(
                id=uuid.uuid4(),
                team_id=team.id,
                type_id=rt.id,
                title=f"[Attention: Stuck Approval] {titles_pool[(i+9) % len(titles_pool)]} #{i+1}",
                description="Request awaiting review and authorization from an authorized approver or team lead.",
                status=RequestStatus.awaiting_start_approval,
                priority=RequestPriority.high,
                owner_id=owner.id,
                created_by=creator.id,
                version=2,
                due_at=now + timedelta(hours=12),
                last_activity_at=stuck_since,
                created_at=created_at,
                updated_at=stuck_since,
            )
            session.add(req)
            session.flush()
            session.add(RequestEvent(
                request_id=req.id,
                actor_id=creator.id,
                type="created",
                to_value={"title": req.title, "status": "new"},
                created_at=created_at,
            ))
            session.add(RequestEvent(
                request_id=req.id,
                actor_id=owner.id,
                type="status_changed",
                from_value={"status": "triage"},
                to_value={"status": "awaiting_start_approval"},
                reason="Requested approval to begin work",
                created_at=stuck_since,
            ))
            requests_created += 1

        # e) Urgent items
        for i in range(15):
            team = teams[i % 3]
            rt = types_by_team[team.id][i % len(types_by_team[team.id])]
            members = team_members_map[team.id]
            creator, owner = members[0], members[1]
            created_at = now - timedelta(hours=random.randint(1, 12))
            req = Request(
                id=uuid.uuid4(),
                team_id=team.id,
                type_id=rt.id,
                title=f"[Attention: URGENT] {titles_pool[(i+12) % len(titles_pool)]} #{i+1}",
                description="P0 Urgent operational request requiring immediate response.",
                status=RequestStatus.in_progress,
                priority=RequestPriority.urgent,
                owner_id=owner.id,
                created_by=creator.id,
                version=2,
                due_at=now + timedelta(hours=4),
                last_activity_at=created_at,
                created_at=created_at,
                updated_at=created_at,
            )
            session.add(req)
            session.flush()
            session.add(RequestEvent(
                request_id=req.id,
                actor_id=creator.id,
                type="created",
                to_value={"title": req.title, "priority": "urgent"},
                created_at=created_at,
            ))
            requests_created += 1

        # f) Fill remaining items to exceed 200 total requests (around 160 more)
        target_remaining = 160
        for i in range(target_remaining):
            team = teams[i % 3]
            team_types = types_by_team[team.id]
            rt = team_types[i % len(team_types)]
            members = team_members_map[team.id]
            creator = random.choice(members)
            req_status = statuses[i % len(statuses)]
            req_priority = priorities[i % len(priorities)]

            # Owner logic
            owner = None
            if req_status not in (RequestStatus.new,):
                owner = random.choice(members)

            created_delta_hours = random.randint(1, 720)
            created_at = now - timedelta(hours=created_delta_hours)
            activity_delta_hours = random.randint(0, created_delta_hours)
            last_activity = now - timedelta(hours=activity_delta_hours)

            due_at = created_at + timedelta(hours=rt.sla_hours or 24)

            req = Request(
                id=uuid.uuid4(),
                team_id=team.id,
                type_id=rt.id,
                title=f"{titles_pool[i % len(titles_pool)]} [Batch {i+1}]",
                description=f"Detailed specifications for operational task {i+1} handled by {team.name}.",
                status=req_status,
                priority=req_priority,
                owner_id=owner.id if owner else None,
                created_by=creator.id,
                version=random.randint(1, 4),
                due_at=due_at,
                last_activity_at=last_activity,
                created_at=created_at,
                updated_at=last_activity,
            )
            session.add(req)
            session.flush()

            # Add creation event
            session.add(RequestEvent(
                request_id=req.id,
                actor_id=creator.id,
                type="created",
                from_value=None,
                to_value={"title": req.title, "status": "new", "priority": req.priority.value},
                reason=None,
                created_at=created_at,
            ))

            # Add status/owner changed events if progressed
            if owner:
                session.add(RequestEvent(
                    request_id=req.id,
                    actor_id=owner.id,
                    type="owner_changed",
                    to_value={"owner_id": str(owner.id), "owner_name": owner.name},
                    reason="Assigned or claimed",
                    created_at=created_at + timedelta(minutes=15),
                ))

            if req_status != RequestStatus.new:
                session.add(RequestEvent(
                    request_id=req.id,
                    actor_id=owner.id if owner else creator.id,
                    type="status_changed",
                    from_value={"status": "new"},
                    to_value={"status": req_status.value},
                    reason="Workflow progression",
                    created_at=last_activity,
                ))

            # Add occasional comments
            if i % 4 == 0:
                comment_author = random.choice(members)
                session.add(Comment(
                    id=uuid.uuid4(),
                    request_id=req.id,
                    author_id=comment_author.id,
                    body=f"Progress update on request #{i+1}: verified prerequisites and ongoing execution.",
                    created_at=last_activity,
                ))

            requests_created += 1

        session.commit()
        print(f"Successfully seeded {requests_created} requests with events and comments!")

    except Exception as e:
        session.rollback()
        print(f"Error during seeding: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()
