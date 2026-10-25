"""Message classification API (local Ollama; no order lookup / no replies)."""

from fastapi import APIRouter, HTTPException

from app.schemas.classification import (
    MessageClassificationRequest,
    MessageClassificationResponse,
)
from app.schemas.errors import ErrorBody, ErrorResponse
from app.services.classification import classify_message
from app.services.ollama_client import OllamaError

router = APIRouter(prefix="/api/v1/demo", tags=["demo-classification"])


@router.post(
    "/message-classifications",
    response_model=MessageClassificationResponse,
    responses={
        422: {"description": "Validation error (blank/oversized message)."},
        502: {"model": ErrorResponse, "description": "Invalid model output."},
        503: {"model": ErrorResponse, "description": "Ollama unavailable or model missing."},
        504: {"model": ErrorResponse, "description": "Ollama inference timeout."},
    },
    summary="Classify a customer message with a local model",
)
async def create_message_classification(
    payload: MessageClassificationRequest,
) -> MessageClassificationResponse:
    """Classify intent and optionally extract an explicit order ID.

    This endpoint does **not** query orders, draft replies, send messages,
    or process refunds. Email/order ownership checks are out of scope here.
    """
    try:
        return await classify_message(payload.message)
    except OllamaError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=ErrorBody(code=exc.code, message=exc.message).model_dump(),
        ) from exc
