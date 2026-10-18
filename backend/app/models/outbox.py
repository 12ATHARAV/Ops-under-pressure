import enum
from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, ForeignKey, Enum, Index, text, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base

JSONType = JSON().with_variant(JSONB, "postgresql")


class OutboxStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    dead = "dead"


class OutboxEntry(Base):
    __tablename__ = "outbox"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    event_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("request_events.id", ondelete="SET NULL"), nullable=True, index=True)
    topic = Column(String(128), nullable=False)
    payload = Column(JSONType, nullable=False)
    status = Column(
        Enum(OutboxStatus, name="outbox_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=OutboxStatus.pending,
        index=True,
    )
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    event = relationship("RequestEvent")

    __table_args__ = (
        Index("ix_outbox_pending_attempt", "next_attempt_at", postgresql_where=text("status = 'pending'")),
    )
