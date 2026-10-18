from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TeamRoleOut(BaseModel):
    team_id: UUID
    team_name: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class UserOut(BaseModel):
    id: UUID
    email: str
    name: str
    created_at: datetime
    teams: list[TeamRoleOut] = []

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
