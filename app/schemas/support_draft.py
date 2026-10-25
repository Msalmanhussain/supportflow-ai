"""Schemas for POST /api/v1/demo/support-drafts.

The model classifies only. Application code retrieves order facts and
policy sections, then renders deterministic draft templates.
Classification is advisory, never authorization. Every successful
response sets requires_human_review=true and is_simulated=true in
application code. Successful generations are persisted for human review.
"""

from __future__ import annotations

import uuid
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.classification import MessageClassificationResponse


DraftOutcome = Literal["draft_ready", "needs_information", "needs_human_review"]
ReviewStatusLiteral = Literal["pending_review", "approved", "rejected"]


class PolicySource(BaseModel):
    """Citation for a retrieved fictional demo policy section."""

    document_id: str
    title: str
    version: str
    section_id: str
    section_title: str
    text: str = Field(
        description="Verbatim section body from the application-owned policy file.",
    )
    demo_label: str = Field(
        description="Explicit demo-policy label from the source document.",
    )


class SupportDraftRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "message": "Where is order SF-1001?",
                    "customer_email": "alex.rivera@example.com",
                }
            ]
        }
    )

    message: str = Field(
        min_length=1,
        max_length=2000,
        description="Customer message (untrusted input).",
    )
    customer_email: Optional[EmailStr] = Field(
        default=None,
        description=(
            "Optional demo ownership email. Required before any order lookup. "
            "Not production identity verification."
        ),
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

    @field_validator("customer_email", mode="before")
    @classmethod
    def normalize_optional_email(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip().lower()
            return cleaned or None
        return value


class SupportDraftResponse(BaseModel):
    """Workflow result after classify → route → template draft (+ persistence)."""

    # Compatibility fields from Phase 2.2/2.3
    classification: MessageClassificationResponse
    outcome: DraftOutcome
    draft_text: str
    requires_human_review: Literal[True] = True
    is_simulated: Literal[True] = True
    sources: list[PolicySource] = Field(default_factory=list)

    # Phase 3.1 persistence
    id: uuid.UUID
    revision: int
    review_status: ReviewStatusLiteral
