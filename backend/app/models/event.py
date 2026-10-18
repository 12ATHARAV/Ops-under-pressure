from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, ForeignKey, Index, desc, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base

JSONType = JSON().with_variant(JSONB, "postgresql")


class RequestEvent(Base):
    __tablename__ = "request_events"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    request_id = Column(UUID(as_uuid=True), ForeignKey("requests.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    type = Column(String(64), nullable=False)
    from_value = Column(JSONType, nullable=True)
    to_value = Column(JSONType, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    request = relationship("Request", back_populates="events")
    actor = relationship("User")

    __table_args__ = (
        Index("ix_request_events_request_id_id", "request_id", desc("id")),
    )
