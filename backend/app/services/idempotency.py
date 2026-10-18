import json
import hashlib
from uuid import UUID
from typing import Callable, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.idempotency import IdempotencyKey


class IdempotencyMismatch(Exception):
    """Raised when an idempotency key is reused with a different request payload (422)."""
    pass


def compute_payload_hash(payload: Any) -> str:
    """Computes a deterministic SHA256 hash of a payload dictionary or object."""
    if payload is None:
        raw = ""
    elif isinstance(payload, (dict, list)):
        raw = json.dumps(payload, sort_keys=True, default=str)
    elif hasattr(payload, "model_dump"):
        raw = json.dumps(payload.model_dump(), sort_keys=True, default=str)
    else:
        raw = str(payload)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def with_idempotency(
    session: Session,
    user_id: UUID,
    key: Optional[str],
    endpoint: str,
    payload: Any,
    operation_fn: Callable[[], Tuple[int, Any]],
) -> Tuple[int, Any]:
    """
    Executes operation_fn with idempotency protection.
    If key is None, executes normally.
    If key is present and matched, returns the previously cached response.
    If key is present with a different payload hash, raises IdempotencyMismatch (422).
    """
    if not key:
        return operation_fn()

    request_hash = compute_payload_hash(payload)

    # 1. Check existing record
    existing = (
        session.query(IdempotencyKey)
        .filter(IdempotencyKey.user_id == user_id, IdempotencyKey.key == key)
        .first()
    )

    if existing:
        if existing.request_hash != request_hash:
            raise IdempotencyMismatch(
                f"Idempotency key '{key}' was previously used with a different request payload"
            )
        return existing.response_status, existing.response_body

    # 2. Execute operation inside transaction/savepoint
    status_code, response_body = operation_fn()

    # Convert Pydantic response or custom dict to JSON-serializable structure
    serializable_body = response_body
    if hasattr(response_body, "model_dump"):
        serializable_body = json.loads(json.dumps(response_body.model_dump(), default=str))
    elif isinstance(response_body, dict):
        serializable_body = json.loads(json.dumps(response_body, default=str))

    # 3. Store idempotency record
    idemp_entry = IdempotencyKey(
        user_id=user_id,
        key=key,
        endpoint=endpoint,
        request_hash=request_hash,
        response_status=status_code,
        response_body=serializable_body,
    )
    session.add(idemp_entry)

    try:
        session.commit()
    except IntegrityError:
        # Concurrent duplicate inserted during execution
        session.rollback()
        existing = (
            session.query(IdempotencyKey)
            .filter(IdempotencyKey.user_id == user_id, IdempotencyKey.key == key)
            .first()
        )
        if existing:
            if existing.request_hash != request_hash:
                raise IdempotencyMismatch(
                    f"Idempotency key '{key}' was previously used with a different request payload"
                )
            return existing.response_status, existing.response_body
        raise

    return status_code, serializable_body
