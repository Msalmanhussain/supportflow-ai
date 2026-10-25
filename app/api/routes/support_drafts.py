"""Support draft workflow API (classify → route → template → persist).

Does not send messages, execute refunds, or invent policy.
Requires an Idempotency-Key header for safe retries.
"""

from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from app.database import SessionLocal
from app.schemas.errors import ErrorBody, ErrorResponse
from app.schemas.support_draft import SupportDraftRequest, SupportDraftResponse
from app.services.ollama_client import OllamaError
from app.services.support_draft import build_support_draft
from app.services.support_request_persistence import (
    PersistenceConflictError,
    find_by_idempotency_key,
    payload_hash,
    persist_generated_draft,
    request_to_draft_response,
)

router = APIRouter(prefix="/api/v1/demo", tags=["demo-support-drafts"])


def _require_idempotency_key(idempotency_key: Optional[str]) -> str:
    if idempotency_key is None or not idempotency_key.strip():
        raise HTTPException(
            status_code=422,
            detail=ErrorBody(
                code="validation_error",
                message="Idempotency-Key header is required.",
            ).model_dump(),
        )
    key = idempotency_key.strip()
    if len(key) > 128:
        raise HTTPException(
            status_code=422,
            detail=ErrorBody(
                code="validation_error",
                message="Idempotency-Key must be at most 128 characters.",
            ).model_dump(),
        )
    return key


@router.post(
    "/support-drafts",
    response_model=SupportDraftResponse,
    responses={
        409: {"model": ErrorResponse, "description": "Idempotency key conflict."},
        422: {
            "description": "Validation error (blank/oversized message, bad email, or missing key)."
        },
        502: {"model": ErrorResponse, "description": "Invalid model output."},
        503: {"model": ErrorResponse, "description": "Ollama unavailable or model missing."},
        504: {"model": ErrorResponse, "description": "Ollama inference timeout."},
    },
    summary="Classify a message, produce a draft, and persist for human review",
)
async def create_support_draft(
    payload: SupportDraftRequest,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
) -> SupportDraftResponse:
    """Orchestrate generation then persist. Inference runs with no DB session open.

    Idempotency:
    - Same key + same payload → return the saved request (no duplicate).
    - Same key + different payload → 409.
    - After a model failure, retrying with the same key is safe (nothing persisted).
    - After a DB failure mid-write, retrying with the same key either completes
      the unique insert or returns the concurrent winner for matching payloads.
    """
    key = _require_idempotency_key(idempotency_key)
    email: Optional[str] = (
        str(payload.customer_email) if payload.customer_email is not None else None
    )

    db = SessionLocal()
    try:
        existing = find_by_idempotency_key(db, key)
        if existing is not None:
            digest = payload_hash(message=payload.message, customer_email=email)
            if existing.idempotency_payload_hash != digest:
                raise HTTPException(
                    status_code=409,
                    detail=ErrorBody(
                        code="idempotency_key_conflict",
                        message="Idempotency key was already used with a different payload.",
                    ).model_dump(),
                )
            return request_to_draft_response(existing)
    finally:
        db.close()

    # No database session held during inference.
    try:
        generated = await build_support_draft(
            message=payload.message,
            customer_email=email,
        )
    except OllamaError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=ErrorBody(code=exc.code, message=exc.message).model_dump(),
        ) from exc

    db = SessionLocal()
    try:
        row = persist_generated_draft(
            db,
            idempotency_key=key,
            message=payload.message,
            customer_email=email,
            generated=generated,
        )
        return request_to_draft_response(row)
    except PersistenceConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail=ErrorBody(code=exc.code, message=exc.message).model_dump(),
        ) from exc
    finally:
        db.close()
