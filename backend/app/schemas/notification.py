from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    id: UUID
    user_id: UUID
    request_id: Optional[UUID] = None
    kind: str
    body: str
    read_at: Optional[datetime] = None
    dedupe_key: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
