"""Classify → route → template draft orchestration.

Boundaries
----------
- The model classifies only (advisory). It never authorizes lookups, refunds,
  policy decisions, or sends.
- Application code verifies order IDs, runs the demo ownership check, retrieves
  policy sections via keyword matching, and renders deterministic templates.
- Customer email, order details, and policy documents are never sent to the model.
- Database sessions for order lookup open only after inference for that branch.
- Persistence of the generated draft is handled by the API layer after this
  function returns (never during inference).
- Every successful workflow result forces requires_human_review=true.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

from app.database import SessionLocal
from app.schemas.classification import MessageClassificationResponse
from app.schemas.support_draft import DraftOutcome, PolicySource
from app.services import draft_templates as templates
from app.services.classification import classify_message
from app.services.ollama_client import OllamaClient
from app.services.order_id_extraction import resolve_order_id
from app.services.order_lookup import lookup_order
from app.services.policy_retrieval import retrieve_policy_sections


@dataclass(frozen=True)
class GeneratedDraft:
    """In-memory workflow result before persistence."""

    classification: MessageClassificationResponse
    outcome: DraftOutcome
    draft_text: str
    sources: list[PolicySource] = field(default_factory=list)
    requires_human_review: bool = True
    is_simulated: bool = True


def _workflow_response(
    classification: MessageClassificationResponse,
    *,
    outcome: DraftOutcome,
    draft_text: str,
    sources: Optional[Sequence[PolicySource]] = None,
) -> GeneratedDraft:
    return GeneratedDraft(
        classification=classification,
        outcome=outcome,
        draft_text=draft_text,
        sources=list(sources or []),
        requires_human_review=True,
        is_simulated=True,
    )


def _handle_order_status(
    classification: MessageClassificationResponse,
    *,
    message: str,
    customer_email: Optional[str],
) -> GeneratedDraft:
    resolution = resolve_order_id(message, model_order_id=classification.order_id)

    if resolution.reason == "missing":
        return _workflow_response(
            classification,
            outcome="needs_information",
            draft_text=templates.draft_needs_order_id(),
        )
    if resolution.reason == "multiple":
        return _workflow_response(
            classification,
            outcome="needs_information",
            draft_text=templates.draft_multiple_order_ids(),
        )
    if resolution.reason in {"invented", "conflict"}:
        return _workflow_response(
            classification,
            outcome="needs_information",
            draft_text=templates.draft_invented_or_conflict_order_id(),
        )

    assert resolution.order_id is not None

    if not customer_email:
        return _workflow_response(
            classification,
            outcome="needs_information",
            draft_text=templates.draft_needs_email(resolution.order_id),
        )

    # Open DB only after inference and ID checks — never during model wait.
    db = SessionLocal()
    try:
        result = lookup_order(
            db,
            order_id=resolution.order_id,
            customer_email=customer_email,
        )
    finally:
        db.close()

    if result.not_found or result.order is None:
        return _workflow_response(
            classification,
            outcome="needs_information",
            draft_text=templates.draft_order_not_found(),
        )

    return _workflow_response(
        classification,
        outcome="draft_ready",
        draft_text=templates.draft_order_status_ready(result.order),
    )


def _handle_return_policy(
    classification: MessageClassificationResponse,
    *,
    message: str,
) -> GeneratedDraft:
    """Retrieve policy sections and template a grounded draft (or hand off)."""
    scored = retrieve_policy_sections(message)
    if not scored:
        return _workflow_response(
            classification,
            outcome="needs_human_review",
            draft_text=templates.draft_return_policy_no_match(),
        )

    sources = [
        PolicySource(
            document_id=item.section.document_id,
            title=item.section.title,
            version=item.section.version,
            section_id=item.section.section_id,
            section_title=item.section.section_title,
            text=item.section.body,
            demo_label=item.section.demo_label,
        )
        for item in scored
    ]
    return _workflow_response(
        classification,
        outcome="draft_ready",
        draft_text=templates.draft_return_policy_ready(sources),
        sources=sources,
    )


async def build_support_draft(
    *,
    message: str,
    customer_email: Optional[str] = None,
    client: Optional[OllamaClient] = None,
) -> GeneratedDraft:
    """Run the support-draft workflow. Does not persist or send."""
    classification = await classify_message(message, client=client)

    if classification.intent == "order_status":
        return _handle_order_status(
            classification,
            message=message,
            customer_email=customer_email,
        )

    if classification.intent == "return_policy":
        return _handle_return_policy(classification, message=message)

    if classification.intent == "refund_request":
        return _workflow_response(
            classification,
            outcome="needs_human_review",
            draft_text=templates.draft_refund_handoff(),
        )

    return _workflow_response(
        classification,
        outcome="needs_human_review",
        draft_text=templates.draft_other_handoff(),
    )
