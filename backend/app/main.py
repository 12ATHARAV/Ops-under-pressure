from fastapi import FastAPI, Request as FastAPIRequest, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.authz.policy import NotFoundError, ForbiddenError
from app.workflow.transitions import (
    IllegalTransition,
    Forbidden as WorkflowForbidden,
    ValidationError as WorkflowValidationError,
)
from app.services.requests import VersionConflict, AlreadyClaimed
from app.services.idempotency import IdempotencyMismatch
from app.routes import (
    auth_router,
    requests_router,
    approvals_router,
    attention_router,
    notifications_router,
    health_router,
    teams_router,
)

app = FastAPI(
    title="Operations Under Pressure",
    description="Operational work items management backend with workflow state machine, optimistic locking, atomic claims, idempotency, and transactional outbox pattern.",
    version="1.0.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(NotFoundError)
def not_found_handler(request: FastAPIRequest, exc: NotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"code": "NOT_FOUND", "message": str(exc), "details": None},
    )


@app.exception_handler(ForbiddenError)
@app.exception_handler(WorkflowForbidden)
def forbidden_handler(request: FastAPIRequest, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"code": "FORBIDDEN", "message": str(exc), "details": None},
    )


@app.exception_handler(IllegalTransition)
def illegal_transition_handler(request: FastAPIRequest, exc: IllegalTransition):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"code": "ILLEGAL_TRANSITION", "message": str(exc), "details": None},
    )


@app.exception_handler(AlreadyClaimed)
def already_claimed_handler(request: FastAPIRequest, exc: AlreadyClaimed):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "code": "ALREADY_CLAIMED",
            "message": str(exc),
            "details": {"owner_name": exc.owner_name},
        },
    )


@app.exception_handler(VersionConflict)
def version_conflict_handler(request: FastAPIRequest, exc: VersionConflict):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "code": "VERSION_CONFLICT",
            "message": str(exc),
            "current": exc.current,
            "events_since_version": exc.events_since_version,
        },
    )


@app.exception_handler(IdempotencyMismatch)
def idempotency_mismatch_handler(request: FastAPIRequest, exc: IdempotencyMismatch):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"code": "IDEMPOTENCY_MISMATCH", "message": str(exc), "details": None},
    )


@app.exception_handler(WorkflowValidationError)
def workflow_validation_handler(request: FastAPIRequest, exc: WorkflowValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"code": "VALIDATION_ERROR", "message": str(exc), "details": None},
    )


@app.exception_handler(RequestValidationError)
def pydantic_validation_handler(request: FastAPIRequest, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": "VALIDATION_ERROR",
            "message": "Invalid request parameters or payload",
            "details": exc.errors(),
        },
    )


# Include Routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(requests_router)
app.include_router(approvals_router)
app.include_router(attention_router)
app.include_router(notifications_router)
app.include_router(teams_router)
