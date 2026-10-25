"""Persist support drafts and apply review mutations with optimistic concurrency.

Transaction boundaries
----------------------
- Inference runs **outside** any database session/transaction.
- Persistence opens a short session only after a successful generation.
- Failed model/database writes do not leave a completed draft row.
- Retry with the same Idempotency-Key after a model failure is safe (no row yet).
- Retry after a successful persist returns the same request (same key + payload).
- Same key with a different payload returns a conflict (409).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Optional

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.models.support_request import (
    ReviewEventAction,
    ReviewStatus,
    SupportRequest,
    SupportReviewEvent,
)
from app.schemas.classification import MessageClassificationResponse
from app.schemas.support_draft import PolicySource, SupportDraftResponse
from app.schemas.support_request import (
    DRAFT_MAX_LENGTH,
    SupportRequestDetail,
    SupportRequestListResponse,
    SupportRequestSummary,
    SupportReviewEventOut,
)
from app.services.classification import PROMPT_VERSION
from app.services.support_draft import GeneratedDraft


class PersistenceConflictError(Exception):
    """Idempotency or revision conflict."""

    code = "conflict"

    def __init__(self, message: str, *, code: str = "conflict") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class RequestNotFoundError(Exception):
    code = "support_request_not_found"

    def __init__(self, message: str = "Support request not found.") -> None:
        super().__init__(message)
        self.message = message


class RequestNotEditableError(Exception):
    code = "support_request_not_editable"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def payload_hash(*, message: str, customer_email: Optional[str]) -> str:
    canonical = json.dumps(
        {"message": message, "customer_email": customer_email},
        separators=(",", ":"),
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _sources_to_json(sources: list[PolicySource]) -> list[dict[str, Any]]:
    return [s.model_dump() for s in sources]


def _sources_from_json(raw: Any) -> list[PolicySource]:
    if not raw:
        return []
    return [PolicySource.model_validate(item) for item in raw]


def _event_out(event: SupportReviewEvent) -> SupportReviewEventOut:
    return SupportReviewEventOut(
        id=event.id,
        action=event.action.value,  # type: ignore[arg-type]
        revision=event.revision,
        note=event.note,
        created_at=event.created_at,
    )


def request_to_detail(row: SupportRequest) -> SupportRequestDetail:
    sources = _sources_from_json(row.sources_snapshot)
    classification = MessageClassificationResponse(
        intent=row.classification_intent,  # type: ignore[arg-type]
        order_id=row.classification_order_id,
        requires_human_review=row.classification_requires_human_review,
    )
    return SupportRequestDetail(
        id=row.id,
        revision=row.revision,
        review_status=row.review_status.value,  # type: ignore[arg-type]
        requires_human_review=True,
        is_simulated=True,
        message=row.message,
        customer_email=row.customer_email,
        classification=classification,
        outcome=row.outcome,  # type: ignore[arg-type]
        draft_text=row.draft_current,
        draft_original=row.draft_original,
        draft_current=row.draft_current,
        sources=sources,
        model_id=row.model_id,
        prompt_version=row.prompt_version,
        reviewed_text=row.reviewed_text,
        created_at=row.created_at,
        updated_at=row.updated_at,
        events=[_event_out(e) for e in row.events],
    )


def request_to_draft_response(row: SupportRequest) -> SupportDraftResponse:
    detail = request_to_detail(row)
    return SupportDraftResponse(
        classification=detail.classification,
        outcome=detail.outcome,
        draft_text=detail.draft_current,
        requires_human_review=True,
        is_simulated=True,
        sources=detail.sources,
        id=detail.id,
        revision=detail.revision,
        review_status=detail.review_status,
    )


def find_by_idempotency_key(db: Session, key: str) -> Optional[SupportRequest]:
    stmt = (
        select(SupportRequest)
        .where(SupportRequest.idempotency_key == key)
        .options(selectinload(SupportRequest.events))
    )
    return db.execute(stmt).scalar_one_or_none()


def persist_generated_draft(
    db: Session,
    *,
    idempotency_key: str,
    message: str,
    customer_email: Optional[str],
    generated: GeneratedDraft,
) -> SupportRequest:
    """Insert a new request or return the existing one for the same key+payload.

    Call only after successful generation. Does not run inference.
    """
    digest = payload_hash(message=message, customer_email=customer_email)
    existing = find_by_idempotency_key(db, idempotency_key)
    if existing is not None:
        if existing.idempotency_payload_hash != digest:
            raise PersistenceConflictError(
                "Idempotency key was already used with a different payload.",
                code="idempotency_key_conflict",
            )
        return existing

    settings = get_settings()
    row = SupportRequest(
        id=uuid.uuid4(),
        idempotency_key=idempotency_key,
        idempotency_payload_hash=digest,
        message=message,
        customer_email=customer_email,
        classification_intent=generated.classification.intent,
        classification_order_id=generated.classification.order_id,
        classification_requires_human_review=generated.classification.requires_human_review,
        outcome=generated.outcome,
        draft_original=generated.draft_text,
        draft_current=generated.draft_text,
        sources_snapshot=_sources_to_json(generated.sources),
        model_id=settings.ollama_model,
        prompt_version=PROMPT_VERSION,
        review_status=ReviewStatus.PENDING_REVIEW,
        requires_human_review=True,
        is_simulated=True,
        revision=1,
        reviewed_text=None,
    )
    event = SupportReviewEvent(
        id=uuid.uuid4(),
        request_id=row.id,
        action=ReviewEventAction.CREATED,
        revision=1,
        note=None,
    )
    db.add(row)
    db.add(event)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Concurrent insert with same key won the race.
        raced = find_by_idempotency_key(db, idempotency_key)
        if raced is None:
            raise
        if raced.idempotency_payload_hash != digest:
            raise PersistenceConflictError(
                "Idempotency key was already used with a different payload.",
                code="idempotency_key_conflict",
            ) from None
        return raced

    db.refresh(row)
    # Reload with events
    loaded = find_by_idempotency_key(db, idempotency_key)
    assert loaded is not None
    return loaded


def list_support_requests(
    db: Session,
    *,
    review_status: Optional[ReviewStatus] = None,
    page: int = 1,
    page_size: int = 20,
) -> SupportRequestListResponse:
    page = max(1, page)
    page_size = min(max(1, page_size), 100)

    filters = []
    if review_status is not None:
        filters.append(SupportRequest.review_status == review_status)

    count_stmt = select(func.count()).select_from(SupportRequest)
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = int(db.execute(count_stmt).scalar_one())

    stmt = select(SupportRequest)
    if filters:
        stmt = stmt.where(*filters)
    stmt = (
        stmt.order_by(SupportRequest.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = list(db.execute(stmt).scalars().all())
    items = [
        SupportRequestSummary(
            id=row.id,
            review_status=row.review_status.value,  # type: ignore[arg-type]
            outcome=row.outcome,  # type: ignore[arg-type]
            classification_intent=row.classification_intent,
            revision=row.revision,
            created_at=row.created_at,
            updated_at=row.updated_at,
            message_preview=(row.message[:120] + "…")
            if len(row.message) > 120
            else row.message,
        )
        for row in rows
    ]
    return SupportRequestListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
    )


def get_support_request(db: Session, request_id: uuid.UUID) -> SupportRequest:
    stmt = (
        select(SupportRequest)
        .where(SupportRequest.id == request_id)
        .options(selectinload(SupportRequest.events))
    )
    row = db.execute(stmt).scalar_one_or_none()
    if row is None:
        raise RequestNotFoundError()
    return row


def edit_draft(
    db: Session,
    *,
    request_id: uuid.UUID,
    draft_text: str,
    expected_revision: int,
) -> SupportRequest:
    cleaned = draft_text.strip()
    if not cleaned:
        raise ValueError("draft_text must not be blank")
    if len(cleaned) > DRAFT_MAX_LENGTH:
        raise ValueError(f"draft_text must be at most {DRAFT_MAX_LENGTH} characters")

    # Terminal states are read-only.
    current = get_support_request(db, request_id)
    if current.review_status != ReviewStatus.PENDING_REVIEW:
        raise RequestNotEditableError(
            "Approved or rejected requests cannot be edited in this phase."
        )

    new_revision = expected_revision + 1
    stmt = (
        update(SupportRequest)
        .where(
            SupportRequest.id == request_id,
            SupportRequest.revision == expected_revision,
            SupportRequest.review_status == ReviewStatus.PENDING_REVIEW,
        )
        .values(
            draft_current=cleaned,
            revision=new_revision,
            updated_at=func.now(),
        )
        .returning(SupportRequest.id)
    )
    updated_id = db.execute(stmt).scalar_one_or_none()
    if updated_id is None:
        db.rollback()
        # Distinguish stale revision vs terminal race
        again = get_support_request(db, request_id)
        if again.review_status != ReviewStatus.PENDING_REVIEW:
            raise RequestNotEditableError(
                "Approved or rejected requests cannot be edited in this phase."
            )
        raise PersistenceConflictError(
            "Stale revision. Reload the request and retry.",
            code="stale_revision",
        )

    event = SupportReviewEvent(
        id=uuid.uuid4(),
        request_id=request_id,
        action=ReviewEventAction.EDITED,
        revision=new_revision,
        note=None,
    )
    db.add(event)
    db.commit()
    return get_support_request(db, request_id)


def decide_review(
    db: Session,
    *,
    request_id: uuid.UUID,
    expected_revision: int,
    approve: bool,
    note: Optional[str] = None,
) -> SupportRequest:
    current = get_support_request(db, request_id)
    if current.review_status != ReviewStatus.PENDING_REVIEW:
        raise RequestNotEditableError(
            "This request already has a terminal review decision."
        )

    new_status = ReviewStatus.APPROVED if approve else ReviewStatus.REJECTED
    new_action = ReviewEventAction.APPROVED if approve else ReviewEventAction.REJECTED
    new_revision = expected_revision + 1
    reviewed_text = current.draft_current if approve else None

    values: dict[str, Any] = {
        "review_status": new_status,
        "revision": new_revision,
        "updated_at": func.now(),
    }
    if approve:
        values["reviewed_text"] = reviewed_text

    stmt = (
        update(SupportRequest)
        .where(
            SupportRequest.id == request_id,
            SupportRequest.revision == expected_revision,
            SupportRequest.review_status == ReviewStatus.PENDING_REVIEW,
        )
        .values(**values)
        .returning(SupportRequest.id)
    )
    updated_id = db.execute(stmt).scalar_one_or_none()
    if updated_id is None:
        db.rollback()
        again = get_support_request(db, request_id)
        if again.review_status != ReviewStatus.PENDING_REVIEW:
            raise RequestNotEditableError(
                "This request already has a terminal review decision."
            )
        raise PersistenceConflictError(
            "Stale revision. Reload the request and retry.",
            code="stale_revision",
        )

    event = SupportReviewEvent(
        id=uuid.uuid4(),
        request_id=request_id,
        action=new_action,
        revision=new_revision,
        note=note,
    )
    db.add(event)
    db.commit()
    return get_support_request(db, request_id)
