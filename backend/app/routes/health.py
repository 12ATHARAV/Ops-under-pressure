from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db import get_db

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint verifying application liveness and database connectivity."""
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "connected",
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "degraded",
                "database": f"error: {str(e)}",
            },
        )
