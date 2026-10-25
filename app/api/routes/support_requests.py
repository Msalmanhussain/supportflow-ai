"""Human review API for persisted support requests (local single-operator demo).

No authenticated reviewer identity. Approval records a local review decision
only — nothing is sent, refunded, or changed on orders.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.support_request import ReviewStatus
from app.schemas.errors import ErrorBody, ErrorResponse
from app.schemas.support_request import (
    DraftEditRequest,
    ReviewDecisionRequest,
    SupportRequestDetail,
    SupportRequestListResponse,
)
from app.services.support_request_persistence import (
    PersistenceConflictError,
    RequestNotEditableError,
    RequestNotFoundError,
    decide_review,
    edit_draft,
    get_support_request,
    list_support_requests,
    request_to_detail,
)

router = APIRouter(prefix="/api/v1/demo", tags=["demo-support-requests"])


def _http_from_domain(exc: Exception) -> HTTPException:
    if isinstance(exc, RequestNotFoundError):
        return HTTPException(
            status_code=404,
            detail=ErrorBody(code=exc.code, message=exc.message).model_dump(),
        )
    if isinstance(exc, PersistenceConflictError):
        return HTTPException(
            status_code=409,
            detail=ErrorBody(code=exc.code, message=exc.message).model_dump(),
        )
    if isinstance(exc, RequestNotEditableError):
        return HTTPException(
            status_code=409,
            detail=ErrorBody(code=exc.code, message=exc.message).model_dump(),
        )
    if isinstance(exc, ValueError):
        return HTTPException(
            status_code=422,
            detail=ErrorBody(code="validation_error", message=str(exc)).model_dump(),
        )
    raise exc


@router.get(
    "/support-requests",
    response_model=SupportRequestListResponse,
    summary="List support requests (paginated, filterable by review status)",
)
def list_requests(
    status: Optional[ReviewStatus] = Query(
        default=None,
        description="Filter by review_status",
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> SupportRequestListResponse:
    return list_support_requests(
        db,
        review_status=status,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/support-requests/{request_id}",
    response_model=SupportRequestDetail,
    responses={404: {"model": ErrorResponse}},
    summary="Get support request detail",
)
def get_request(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> SupportRequestDetail:
    try:
        row = get_support_request(db, request_id)
    except RequestNotFoundError as exc:
        raise _http_from_domain(exc) from exc
    return request_to_detail(row)


@router.patch(
    "/support-requests/{request_id}/draft",
    response_model=SupportRequestDetail,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"description": "Blank or oversized draft / validation error."},
    },
    summary="Edit pending draft (optimistic concurrency via expected_revision)",
)
def patch_draft(
    request_id: uuid.UUID,
    payload: DraftEditRequest,
    db: Session = Depends(get_db),
) -> SupportRequestDetail:
    try:
        row = edit_draft(
            db,
            request_id=request_id,
            draft_text=payload.draft_text,
            expected_revision=payload.expected_revision,
        )
    except (RequestNotFoundError, PersistenceConflictError, RequestNotEditableError, ValueError) as exc:
        raise _http_from_domain(exc) from exc
    return request_to_detail(row)


@router.post(
    "/support-requests/{request_id}/approve",
    response_model=SupportRequestDetail,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
    summary="Approve pending draft (stores exact reviewed text; nothing is sent)",
)
def approve_request(
    request_id: uuid.UUID,
    payload: ReviewDecisionRequest,
    db: Session = Depends(get_db),
) -> SupportRequestDetail:
    try:
        row = decide_review(
            db,
            request_id=request_id,
            expected_revision=payload.expected_revision,
            approve=True,
            note=payload.note,
        )
    except (RequestNotFoundError, PersistenceConflictError, RequestNotEditableError) as exc:
        raise _http_from_domain(exc) from exc
    return request_to_detail(row)


@router.post(
    "/support-requests/{request_id}/reject",
    response_model=SupportRequestDetail,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
    summary="Reject pending draft (local decision only; nothing is sent)",
)
def reject_request(
    request_id: uuid.UUID,
    payload: ReviewDecisionRequest,
    db: Session = Depends(get_db),
) -> SupportRequestDetail:
    try:
        row = decide_review(
            db,
            request_id=request_id,
            expected_revision=payload.expected_revision,
            approve=False,
            note=payload.note,
        )
    except (RequestNotFoundError, PersistenceConflictError, RequestNotEditableError) as exc:
        raise _http_from_domain(exc) from exc
    return request_to_detail(row)
