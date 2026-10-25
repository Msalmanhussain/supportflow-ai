"""Deterministic classification fixtures for test/acceptance only.

Enabled only when Settings.allows_inference_fixture is True
(APP_ENV in {test, acceptance} AND INFERENCE_FIXTURE=true).

This is not exposed as a normal-application bypass: development and
production ignore the flag entirely.
"""

from __future__ import annotations

from app.schemas.classification import MessageClassificationResponse
from app.services.ollama_client import OllamaUnavailableError


# Marker substrings used by browser acceptance tests (synthetic only).
MARKER_ORDER = "ACCEPTANCE_ORDER_SF1001"
MARKER_POLICY = "ACCEPTANCE_POLICY_WINDOW"
MARKER_REFUND = "ACCEPTANCE_REFUND_HANDOFF"
MARKER_NEEDS_ID = "ACCEPTANCE_ORDER_NO_ID"
MARKER_UNAVAILABLE = "ACCEPTANCE_FORCE_OLLAMA_UNAVAILABLE"


def classify_with_fixture(message: str) -> MessageClassificationResponse:
    """Return a fixed classification or raise a simulated Ollama outage."""
    if MARKER_UNAVAILABLE in message:
        raise OllamaUnavailableError("The local Ollama service is unavailable.")

    if MARKER_ORDER in message:
        return MessageClassificationResponse(
            intent="order_status",
            order_id="SF-1001",
            requires_human_review=False,
        )
    if MARKER_NEEDS_ID in message:
        return MessageClassificationResponse(
            intent="order_status",
            order_id=None,
            requires_human_review=False,
        )
    if MARKER_POLICY in message:
        return MessageClassificationResponse(
            intent="return_policy",
            order_id=None,
            requires_human_review=True,
        )
    if MARKER_REFUND in message:
        return MessageClassificationResponse(
            intent="refund_request",
            order_id=None,
            requires_human_review=False,
        )

    # Default fixture: other → human review handoff
    return MessageClassificationResponse(
        intent="other",
        order_id=None,
        requires_human_review=True,
    )
