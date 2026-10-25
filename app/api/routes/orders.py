"""Synthetic order lookup API.

Ownership note
--------------
``customer_email`` matching is a **demo ownership check only**. It is not
production identity verification. Knowing an order ID alone must not expose
order details; a mismatched or unknown pair yields the same generic not-found
response.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.errors import ErrorBody, ErrorResponse
from app.schemas.order import OrderLookupRequest, OrderLookupResponse
from app.services.order_lookup import (
    NOT_FOUND_CODE,
    NOT_FOUND_MESSAGE,
    lookup_order,
)

router = APIRouter(prefix="/api/v1/demo", tags=["demo-orders"])


@router.post(
    "/order-lookups",
    response_model=OrderLookupResponse,
    responses={
        404: {"model": ErrorResponse, "description": "No matching synthetic order."},
        422: {"description": "Validation error (missing/invalid fields)."},
    },
    summary="Look up a synthetic order (demo ownership check)",
)
def create_order_lookup(
    payload: OrderLookupRequest,
    db: Session = Depends(get_db),
) -> OrderLookupResponse:
    """Require both ``order_id`` and ``customer_email``; return details only on match.

    Simulated tracking is **not** live courier tracking. Responses always set
    ``is_simulated`` to ``true``.
    """
    result = lookup_order(
        db,
        order_id=payload.order_id,
        customer_email=str(payload.customer_email),
    )
    if result.not_found or result.order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorBody(
                code=NOT_FOUND_CODE,
                message=NOT_FOUND_MESSAGE,
            ).model_dump(),
        )
    return result.order
