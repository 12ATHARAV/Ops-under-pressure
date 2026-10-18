import uuid
import enum
from sqlalchemy import Column, String, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db import Base


class TeamRole(str, enum.Enum):
    member = "member"
    approver = "approver"
    lead = "lead"


class Team(Base):
    __tablename__ = "teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)

    # Relationships
    memberships = relationship("TeamMembership", back_populates="team", cascade="all, delete-orphan")
    request_types = relationship("RequestType", back_populates="team", cascade="all, delete-orphan")
    requests = relationship("Request", back_populates="team", cascade="all, delete-orphan")


class TeamMembership(Base):
    __tablename__ = "team_memberships"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True)
    role = Column(
        Enum(TeamRole, name="team_role", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=TeamRole.member,
    )

    # Relationships
    user = relationship("User", back_populates="memberships")
    team = relationship("Team", back_populates="memberships")
