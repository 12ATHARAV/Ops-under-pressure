import pytest
from datetime import datetime, timezone
from starlette.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db import SessionLocal
from app.config import settings
from app.auth.security import create_access_token
from app.models.user import User
from app.models.team import Team, TeamMembership, TeamRole
from app.models.request import RequestType, Request, ApprovalMode, RequestStatus, RequestPriority
from app.seed import seed_database


@pytest.fixture(scope="session", autouse=True)
def setup_seed_data():
    """Ensure database has migrated schema and seeded baseline data for testing."""
    seed_database()


@pytest.fixture
def db_session():
    """Yields a database session for direct inspection or teardown."""
    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """FastAPI TestClient instance."""
    return TestClient(app)


@pytest.fixture
def alice_auth_headers(db_session: Session) -> dict[str, str]:
    """Alice is Lead in Platform Engineering, Approver in Security."""
    alice = db_session.query(User).filter(User.email == "alice@example.com").first()
    token = create_access_token({"sub": str(alice.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def bob_auth_headers(db_session: Session) -> dict[str, str]:
    """Bob is Approver in Platform Engineering, Member in Customer Operations."""
    bob = db_session.query(User).filter(User.email == "bob@example.com").first()
    token = create_access_token({"sub": str(bob.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def charlie_auth_headers(db_session: Session) -> dict[str, str]:
    """Charlie is Member in Platform Engineering only."""
    charlie = db_session.query(User).filter(User.email == "charlie@example.com").first()
    token = create_access_token({"sub": str(charlie.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def henry_auth_headers(db_session: Session) -> dict[str, str]:
    """Henry is Member in Customer Operations only (non-member for Platform)."""
    henry = db_session.query(User).filter(User.email == "henry@example.com").first()
    token = create_access_token({"sub": str(henry.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def platform_team(db_session: Session) -> Team:
    return db_session.query(Team).filter(Team.name == "Platform Engineering").first()


@pytest.fixture
def platform_types(db_session: Session, platform_team: Team) -> dict[str, RequestType]:
    types = db_session.query(RequestType).filter(RequestType.team_id == platform_team.id).all()
    return {
        t.approval_mode.value if hasattr(t.approval_mode, "value") else str(t.approval_mode): t
        for t in types
    }
