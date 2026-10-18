import uuid
import enum
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    DateTime,
    ForeignKey,
    Enum,
    Index,
    Computed,
    desc,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
from sqlalchemy.types import TypeDecorator
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base


class TSVectorType(TypeDecorator):
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(TSVECTOR())
        return dialect.type_descriptor(Text())


class ApprovalMode(str, enum.Enum):
    none = "none"
    before = "before"
    after = "after"
    both = "both"


class RequestStatus(str, enum.Enum):
    new = "new"
    triage = "triage"
    awaiting_start_approval = "awaiting_start_approval"
    in_progress = "in_progress"
    awaiting_completion_approval = "awaiting_completion_approval"
    done = "done"
    cancelled = "cancelled"


class RequestPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class RequestType(Base):
    __tablename__ = "request_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    approval_mode = Column(
        Enum(ApprovalMode, name="approval_mode", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ApprovalMode.none,
    )
    sla_hours = Column(Integer, nullable=True)

    # Relationships
    team = relationship("Team", back_populates="request_types")
    requests = relationship("Request", back_populates="request_type", cascade="all, delete-orphan")


class Request(Base):
    __tablename__ = "requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    type_id = Column(UUID(as_uuid=True), ForeignKey("request_types.id", ondelete="RESTRICT"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False, default="")
    status = Column(
        Enum(RequestStatus, name="request_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=RequestStatus.new,
        index=True,
    )
    priority = Column(
        Enum(RequestPriority, name="request_priority", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=RequestPriority.medium,
        index=True,
    )
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    due_at = Column(DateTime(timezone=True), nullable=True)
    last_activity_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    search_tsv = Column(
        TSVectorType(),
        Computed("to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, ''))", persisted=True),
        nullable=True,
    )

    # Relationships
    team = relationship("Team", back_populates="requests")
    request_type = relationship("RequestType", back_populates="requests")
    owner = relationship("User", foreign_keys=[owner_id], back_populates="owned_requests")
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_requests")
    events = relationship("RequestEvent", back_populates="request", cascade="all, delete-orphan", order_by="desc(RequestEvent.id)")
    comments = relationship("Comment", back_populates="request", cascade="all, delete-orphan", order_by="Comment.created_at")

    __table_args__ = (
        Index("ix_requests_team_status_activity_id", "team_id", "status", desc("last_activity_at"), desc("id")),
        Index("ix_requests_owner_status", "owner_id", "status"),
        Index(
            "ix_requests_unowned_inbox",
            "team_id",
            "created_at",
            postgresql_where=text("owner_id IS NULL AND status IN ('new', 'triage')"),
        ),
        Index(
            "ix_requests_active_stale",
            "team_id",
            "last_activity_at",
            postgresql_where=text("status NOT IN ('done', 'cancelled')"),
        ),
        Index("ix_requests_search_tsv", "search_tsv", postgresql_using="gin"),
    )


class Comment(Base):
    __tablename__ = "comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID(as_uuid=True), ForeignKey("requests.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    request = relationship("Request", back_populates="comments")
    author = relationship("User", back_populates="comments")
