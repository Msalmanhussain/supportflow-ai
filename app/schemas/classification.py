"""Schemas for POST /api/v1/demo/message-classifications."""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


ClassificationIntent = Literal[
    "order_status",
    "return_policy",
    "refund_request",
    "other",
]


class MessageClassificationRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "message": "Where is order SF-1001? It has not arrived yet.",
                }
            ]
        }
    )

    message: str = Field(
        min_length=1,
        max_length=2000,
        description="Customer message to classify (untrusted input).",
    )

    @field_validator("message")
    @classmethod
    def strip_and_reject_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("message must not be blank")
        if len(cleaned) > 2000:
            raise ValueError("message must be at most 2000 characters")
        return cleaned


class MessageClassificationResponse(BaseModel):
    """Validated classification result after application review rules."""

    intent: ClassificationIntent
    order_id: Optional[str] = Field(
        default=None,
        description="Order ID only when explicitly present in the message.",
    )
    requires_human_review: bool = Field(
        description=(
            "Application-enforced review flag. Always true for refund_request "
            "and other; never treated as model-authorized confidence."
        ),
    )


# JSON Schema passed to Ollama `format` for schema-constrained generation.
CLASSIFICATION_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": [
                "order_status",
                "return_policy",
                "refund_request",
                "other",
            ],
        },
        "order_id": {
            "anyOf": [{"type": "string"}, {"type": "null"}],
        },
        "requires_human_review": {"type": "boolean"},
    },
    "required": ["intent", "order_id", "requires_human_review"],
    "additionalProperties": False,
}
