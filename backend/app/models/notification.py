import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index, desc
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    request_id = Column(UUID(as_uuid=True), ForeignKey("requests.id", ondelete="CASCADE"), nullable=True, index=True)
    kind = Column(String(64), nullable=False)
    body = Column(Text, nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    dedupe_key = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="notifications")
    request = relationship("Request")

    __table_args__ = (
        Index("ix_notifications_user_created_id", "user_id", desc("created_at"), desc("id")),
    )
