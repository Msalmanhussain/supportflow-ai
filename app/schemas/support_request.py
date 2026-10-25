"""Schemas for persisted support requests and review mutations."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.classification import MessageClassificationResponse
from app.schemas.support_draft import DraftOutcome, PolicySource


ReviewStatusLiteral = Literal["pending_review", "approved", "rejected"]
ReviewEventActionLiteral = Literal["created", "edited", "approved", "rejected"]

DRAFT_MAX_LENGTH = 10_000


class SupportReviewEventOut(BaseModel):
    id: uuid.UUID
    action: ReviewEventActionLiteral
    revision: int
    note: Optional[str] = None
    created_at: datetime


class SupportRequestSummary(BaseModel):
    id: uuid.UUID
    review_status: ReviewStatusLiteral
    outcome: DraftOutcome
    classification_intent: str
    revision: int
    created_at: datetime
    updated_at: datetime
    message_preview: str


class SupportRequestDetail(BaseModel):
    """Full persisted request including original response-compatible fields."""

    model_config = ConfigDict(from_attributes=False)

    id: uuid.UUID
    revision: int
    review_status: ReviewStatusLiteral
    requires_human_review: Literal[True] = True
    is_simulated: Literal[True] = True

    message: str
    customer_email: Optional[str] = None

    classification: MessageClassificationResponse
    outcome: DraftOutcome
    draft_text: str = Field(description="Current editable draft (alias of draft_current).")
    draft_original: str
    draft_current: str
    sources: list[PolicySource]

    model_id: str
    prompt_version: str
    reviewed_text: Optional[str] = None

    created_at: datetime
    updated_at: datetime
    events: list[SupportReviewEventOut] = Field(default_factory=list)


class SupportRequestListResponse(BaseModel):
    items: list[SupportRequestSummary]
    page: int
    page_size: int
    total: int


class DraftEditRequest(BaseModel):
    draft_text: str = Field(min_length=1, max_length=DRAFT_MAX_LENGTH)
    expected_revision: int = Field(ge=1)

    @field_validator("draft_text")
    @classmethod
    def strip_reject_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("draft_text must not be blank")
        if len(cleaned) > DRAFT_MAX_LENGTH:
            raise ValueError(f"draft_text must be at most {DRAFT_MAX_LENGTH} characters")
        return cleaned


class ReviewDecisionRequest(BaseModel):
    expected_revision: int = Field(ge=1)
    note: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("note", mode="before")
    @classmethod
    def normalize_note(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return value
