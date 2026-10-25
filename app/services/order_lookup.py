"""Synthetic order lookup with demo ownership matching.

Email matching is a demo ownership check only, not production identity
verification. Nonexistent orders and mismatched emails share one generic
not-found response so callers cannot probe for valid order IDs.
"""

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Customer, Order
from app.schemas.order import OrderLookupResponse


NOT_FOUND_CODE = "order_not_found"
NOT_FOUND_MESSAGE = (
    "No matching synthetic order was found for the provided order_id and "
    "customer_email."
)


@dataclass(frozen=True)
class LookupResult:
    order: Optional[OrderLookupResponse]
    not_found: bool


def lookup_order(
    db: Session,
    *,
    order_id: str,
    customer_email: str,
) -> LookupResult:
    """Return order details only when order_id and customer_email both match."""
    stmt = (
        select(Order)
        .join(Customer)
        .where(Order.order_id == order_id)
        .where(func.lower(Customer.email) == customer_email.lower())
    )
    order = db.execute(stmt).scalar_one_or_none()
    if order is None:
        return LookupResult(order=None, not_found=True)

    return LookupResult(
        order=OrderLookupResponse(
            order_id=order.order_id,
            status=order.status.display_label,
            courier=order.courier,
            estimated_delivery=order.estimated_delivery,
            last_update=order.last_update,
            is_simulated=True,
        ),
        not_found=False,
    )
