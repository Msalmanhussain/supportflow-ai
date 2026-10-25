"""Persistent support requests and append-only review events."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ReviewStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReviewEventAction(str, Enum):
    CREATED = "created"
    EDITED = "edited"
    APPROVED = "approved"
    REJECTED = "rejected"


class SupportRequest(Base):
    """A generated support draft awaiting (or after) local human review.

    This is a single-operator local demo. There is no authenticated reviewer
    identity — approval only records that a local review decision was made.
    """

    __tablename__ = "support_requests"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_support_requests_idempotency_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    message: Mapped[str] = mapped_column(Text, nullable=False)
    customer_email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)

    classification_intent: Mapped[str] = mapped_column(String(64), nullable=False)
    classification_order_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    classification_requires_human_review: Mapped[bool] = mapped_column(nullable=False)

    outcome: Mapped[str] = mapped_column(String(64), nullable=False)
    draft_original: Mapped[str] = mapped_column(Text, nullable=False)
    draft_current: Mapped[str] = mapped_column(Text, nullable=False)
    sources_snapshot: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)

    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)

    review_status: Mapped[ReviewStatus] = mapped_column(
        SAEnum(
            ReviewStatus,
            name="review_status",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
            native_enum=True,
        ),
        nullable=False,
        default=ReviewStatus.PENDING_REVIEW,
    )
    requires_human_review: Mapped[bool] = mapped_column(nullable=False, default=True)
    is_simulated: Mapped[bool] = mapped_column(nullable=False, default=True)

    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reviewed_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    events: Mapped[list["SupportReviewEvent"]] = relationship(
        back_populates="request",
        order_by="SupportReviewEvent.created_at",
        cascade="all, delete-orphan",
    )


class SupportReviewEvent(Base):
    """Append-only review history. No secrets; no verified reviewer identity."""

    __tablename__ = "support_review_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("support_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[ReviewEventAction] = mapped_column(
        SAEnum(
            ReviewEventAction,
            name="review_event_action",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
            native_enum=True,
        ),
        nullable=False,
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    request: Mapped["SupportRequest"] = relationship(back_populates="events")
