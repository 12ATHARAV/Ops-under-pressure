from uuid import UUID
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


class RequestEventOut(BaseModel):
    id: int
    request_id: UUID
    actor_id: UUID
    actor_name: Optional[str] = None
    type: str
    from_value: Optional[Any] = None
    to_value: Optional[Any] = None
    reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
