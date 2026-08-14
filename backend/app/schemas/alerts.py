from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AlertResponse(BaseModel):
    id: int
    type: str
    severity: str
    symbol: str | None
    title: str
    message: str
    is_read: bool
    created_at: datetime
    metadata: dict[str, Any] | None = None
