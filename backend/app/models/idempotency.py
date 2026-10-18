from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db import Base

JSONType = JSON().with_variant(JSONB, "postgresql")


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    key = Column(String(255), primary_key=True)
    endpoint = Column(String(255), nullable=False)
    request_hash = Column(String(64), nullable=False)
    response_status = Column(Integer, nullable=False)
    response_body = Column(JSONType, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
