"""Extract and validate order identifiers from untrusted customer text.

Application code — not the model — decides which identifiers are usable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Sequence

# Synthetic SupportFlow IDs (SF-1001) plus similar PREFIX-digits tokens (ABC-1).
_ORDER_ID_PATTERN = re.compile(r"\b([A-Za-z]{2,}-\d+)\b")


@dataclass(frozen=True)
class OrderIdResolution:
    """Result of resolving an order ID from message text + model hint."""

    order_id: Optional[str]
    reason: Optional[str]
    """Machine-oriented reason when order_id is None: missing | multiple | invented | conflict."""


def extract_order_ids(message: str) -> list[str]:
    """Return unique order-like IDs in first-seen order (case-preserving)."""
    seen: set[str] = set()
    ordered: list[str] = []
    for match in _ORDER_ID_PATTERN.finditer(message):
        token = match.group(1)
        key = token.casefold()
        if key not in seen:
            seen.add(key)
            ordered.append(token)
    return ordered


def resolve_order_id(
    message: str,
    *,
    model_order_id: Optional[str],
) -> OrderIdResolution:
    """Require one unambiguous ID present in the message.

    The model-extracted ID is advisory. It is accepted only when it matches
    an ID that already appears in the customer text. Invented IDs are rejected.
    """
    found = extract_order_ids(message)
    model_clean = (
        str(model_order_id).strip()
        if model_order_id is not None and str(model_order_id).strip()
        else None
    )

    if not found:
        # Model-only ID with no textual support is treated as invented.
        if model_clean is not None:
            return OrderIdResolution(order_id=None, reason="invented")
        return OrderIdResolution(order_id=None, reason="missing")
    if len(found) > 1:
        return OrderIdResolution(order_id=None, reason="multiple")

    only = found[0]
    if model_clean is None:
        return OrderIdResolution(order_id=only, reason=None)

    present = {token.casefold() for token in found}
    if model_clean.casefold() not in present:
        # Model invented an ID that is not in the customer text.
        return OrderIdResolution(order_id=None, reason="invented")
    if model_clean.casefold() != only.casefold():
        return OrderIdResolution(order_id=None, reason="conflict")
    return OrderIdResolution(order_id=only, reason=None)


def ids_appear_in_message(message: str, candidates: Sequence[str]) -> bool:
    """True when every candidate token appears as an extracted ID in message."""
    present = {token.casefold() for token in extract_order_ids(message)}
    return all(c.strip().casefold() in present for c in candidates if c and c.strip())
