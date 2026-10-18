from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.db import get_db
from app.models.user import User
from app.models.team import TeamMembership
from app.schemas.auth import LoginRequest, TokenResponse, UserOut, TeamRoleOut
from app.auth.security import verify_password, create_access_token
from app.auth.deps import get_current_user

router = APIRouter(tags=["Auth"])


def format_user_out(user: User) -> UserOut:
    teams_out = [
        TeamRoleOut(
            team_id=m.team_id,
            team_name=m.team.name if m.team else "Unknown",
            role=m.role.value if hasattr(m.role, "value") else str(m.role),
        )
        for m in user.memberships
    ]
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        created_at=user.created_at,
        teams=teams_out,
    )


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .options(joinedload(User.memberships).joinedload(TeamMembership.team))
        .filter(User.email == payload.email)
        .first()
    )
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=format_user_out(user),
    )


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return format_user_out(current_user)
