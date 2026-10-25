"""Order lookup request/response schemas.

IMPORTANT — demo ownership check only:
Matching ``order_id`` + ``customer_email`` is a portfolio demonstration of
ownership gating. It is NOT production-grade identity verification.
"""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class OrderLookupRequest(BaseModel):
    """Both fields are required. Email is a demo ownership check only."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "order_id": "SF-1001",
                    "customer_email": "alex.rivera@example.com",
                }
            ]
        }
    )

    order_id: str = Field(
        min_length=1,
        max_length=64,
        description="Public synthetic order identifier.",
    )
    customer_email: EmailStr = Field(
        description=(
            "Customer email used as a DEMO ownership check only — "
            "not production identity verification."
        ),
    )

    @field_validator("order_id")
    @classmethod
    def strip_order_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("order_id must not be blank")
        return cleaned

    @field_validator("customer_email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value


class OrderLookupResponse(BaseModel):
    """Public order payload. Never includes customer PII or internal IDs.

    Date/time formats:
    - ``estimated_delivery``: ISO calendar date ``YYYY-MM-DD`` (or null).
    - ``last_update``: ISO 8601 datetime with timezone offset
      (UTC, e.g. ``2026-03-15T14:30:00+00:00``).
    """

    order_id: str
    status: str = Field(description="Human-readable synthetic status label.")
    courier: Optional[str] = Field(
        description="Fictional courier name, or null when not applicable.",
    )
    estimated_delivery: Optional[date] = Field(
        description="ISO date YYYY-MM-DD, or null.",
    )
    last_update: datetime = Field(
        description="Timezone-aware ISO 8601 timestamp (UTC).",
    )
    is_simulated: Literal[True] = Field(
        default=True,
        description="Always true — this is simulated tracking, not live courier data.",
    )
