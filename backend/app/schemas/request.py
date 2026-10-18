from uuid import UUID
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from app.models.request import ApprovalMode, RequestStatus, RequestPriority


class RequestTypeOut(BaseModel):
    id: UUID
    team_id: UUID
    name: str
    approval_mode: ApprovalMode
    sla_hours: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class RequestCreate(BaseModel):
    team_id: UUID
    type_id: UUID
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="")
    priority: RequestPriority = RequestPriority.medium


class RequestEdit(BaseModel):
    version: int
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Optional[RequestPriority] = None
    due_at: Optional[datetime] = None


class RequestAssign(BaseModel):
    version: int
    owner_id: UUID
    reason: Optional[str] = None


class RequestTransition(BaseModel):
    version: int
    to: RequestStatus
    reason: Optional[str] = None


class CommentCreate(BaseModel):
    body: str = Field(..., min_length=1)


class CommentOut(BaseModel):
    id: UUID
    request_id: UUID
    author_id: UUID
    author_name: Optional[str] = None
    body: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RequestListOut(BaseModel):
    id: UUID
    team_id: UUID
    team_name: Optional[str] = None
    type_id: UUID
    type_name: Optional[str] = None
    approval_mode: Optional[ApprovalMode] = None
    title: str
    description: str
    status: RequestStatus
    priority: RequestPriority
    owner_id: Optional[UUID] = None
    owner_name: Optional[str] = None
    created_by: UUID
    creator_name: Optional[str] = None
    version: int
    due_at: Optional[datetime] = None
    last_activity_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RequestDetailOut(RequestListOut):
    allowed_actions: list[str] = []
    sla_hours: Optional[int] = None
    comments: list[CommentOut] = []

    model_config = ConfigDict(from_attributes=True)


class VersionConflictResponse(BaseModel):
    code: str = "VERSION_CONFLICT"
    message: str = "Request has been modified by another transaction"
    current: dict[str, Any]
    events_since_version: list[dict[str, Any]]
