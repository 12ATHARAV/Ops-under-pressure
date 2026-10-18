import base64
import json
from datetime import datetime
from typing import Generic, TypeVar, Any, Optional
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: Optional[str] = None
    has_more: bool = False

    model_config = ConfigDict(from_attributes=True)


def encode_cursor(timestamp: datetime, row_id: Any) -> str:
    """Encode a (timestamp, id) pair into a URL-safe base64 string."""
    payload = [timestamp.isoformat(), str(row_id)]
    data = json.dumps(payload).encode("utf-8")
    return base64.urlsafe_b64encode(data).decode("utf-8")


def decode_cursor(cursor_str: str) -> tuple[datetime, str]:
    """Decode a URL-safe base64 string back into (timestamp, id)."""
    try:
        data = base64.urlsafe_b64decode(cursor_str.encode("utf-8"))
        payload = json.loads(data.decode("utf-8"))
        ts = datetime.fromisoformat(payload[0])
        return ts, payload[1]
    except Exception as e:
        raise ValueError(f"Invalid cursor format: {e}")
