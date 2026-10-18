from app.routes.auth import router as auth_router
from app.routes.requests import router as requests_router
from app.routes.approvals import router as approvals_router
from app.routes.attention import router as attention_router
from app.routes.notifications import router as notifications_router
from app.routes.health import router as health_router
from app.routes.teams import router as teams_router

__all__ = [
    "auth_router",
    "requests_router",
    "approvals_router",
    "attention_router",
    "notifications_router",
    "health_router",
    "teams_router",
]
