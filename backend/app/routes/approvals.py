from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.user import User
from app.auth.deps import get_current_user
from app.services.queries import get_approval_queue

router = APIRouter(prefix="/approvals", tags=["Approvals"])


@router.get("/queue", response_model=list[dict[str, Any]])
def get_user_approval_queue(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetches all requests awaiting approval across the caller's authorized teams."""
    return get_approval_queue(session=db, user=current_user)
