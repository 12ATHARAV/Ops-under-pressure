from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.user import User
from app.auth.deps import get_current_user
from app.services.attention import get_attention_buckets

router = APIRouter(prefix="/attention", tags=["Attention"])


@router.get("", response_model=dict[str, Any])
def get_attention_view(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns prioritized buckets (unowned, stale, overdue, stuck approval, urgent)
    for teams where the user has a 'lead' role.
    """
    return get_attention_buckets(user=current_user, session=db)
