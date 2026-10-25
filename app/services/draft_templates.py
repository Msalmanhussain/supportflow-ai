"""Deterministic reply templates for support drafts.

The local model classifies intent only. Application code retrieves verified
order facts and policy sections (when applicable) and renders these templates.
No second model call generates customer-facing text.
"""

from __future__ import annotations

from typing import Sequence

from app.schemas.order import OrderLookupResponse
from app.schemas.support_draft import PolicySource


def draft_order_status_ready(order: OrderLookupResponse) -> str:
    courier = order.courier or "Not available"
    eta = (
        order.estimated_delivery.isoformat()
        if order.estimated_delivery is not None
        else "Not available"
    )
    last_update = order.last_update.isoformat()
    return (
        f"Thank you for contacting SupportFlow about order {order.order_id}.\n\n"
        f"Based on our simulated order records (not live courier tracking):\n"
        f"- Status: {order.status}\n"
        f"- Courier: {courier}\n"
        f"- Estimated delivery: {eta}\n"
        f"- Last update: {last_update}\n\n"
        "If anything looks incorrect, reply with more detail and a teammate "
        "will review before any customer-facing send."
    )


def draft_needs_order_id() -> str:
    return (
        "Thanks for reaching out about your order status. "
        "Please reply with your order ID (for example SF-1001) so we can "
        "look up the simulated record. A human must approve any reply before it is sent."
    )


def draft_needs_email(order_id: str) -> str:
    return (
        f"We found order ID {order_id} in your message. "
        "Please provide the customer email used at purchase so we can complete "
        "the demo ownership check. We will not look up order details without it. "
        "A human must approve any reply before it is sent."
    )


def draft_multiple_order_ids() -> str:
    return (
        "Your message mentions more than one order ID. "
        "Please reply with a single order ID so we know which simulated order "
        "to check. A human must approve any reply before it is sent."
    )


def draft_invented_or_conflict_order_id() -> str:
    return (
        "We could not confirm a single order ID from your message. "
        "Please reply with the exact order ID as it appears on your receipt "
        "(for example SF-1001). A human must approve any reply before it is sent."
    )


def draft_order_not_found() -> str:
    """Generic clarification — same tone whether order or email mismatched."""
    return (
        "We could not find a matching simulated order for the order ID and "
        "customer email provided. Please double-check both values and try again. "
        "For privacy in this demo, we do not confirm which field was wrong. "
        "A human must approve any reply before it is sent."
    )


def draft_return_policy_ready(sources: Sequence[PolicySource]) -> str:
    """Build a draft from verbatim retrieved policy sections only."""
    blocks: list[str] = [
        "Thanks for asking about the SupportFlow demo store policy.",
        "The following text is copied from our fictional demo policy documents "
        "(not legal advice; not a real merchant policy). "
        "It does not decide eligibility for your specific order.",
        "",
    ]
    for source in sources:
        blocks.append(
            f"[{source.document_id} · {source.title} · v{source.version} · "
            f"section {source.section_id} — {source.section_title}]"
        )
        blocks.append(source.demo_label)
        blocks.append(source.text)
        blocks.append("")
    blocks.append(
        "A human must approve any reply before it is sent. "
        "We will not invent additional policy rules beyond the cited sections."
    )
    return "\n".join(blocks).strip() + "\n"


def draft_return_policy_no_match() -> str:
    return (
        "Thanks for asking about our demo store policy. "
        "We could not match your question to a specific policy section with our "
        "keyword retrieval, so a teammate needs to review before answering. "
        "We will not invent policy details. A human must approve any reply before it is sent."
    )


def draft_return_policy_handoff() -> str:
    """Backward-compatible alias for no-match / review handoff."""
    return draft_return_policy_no_match()


def draft_refund_handoff() -> str:
    return (
        "We received your refund request. "
        "Refunds are never promised or executed automatically in this demo. "
        "A teammate will review your request before any further action. "
        "A human must approve any reply before it is sent."
    )


def draft_other_handoff() -> str:
    return (
        "Thanks for contacting SupportFlow. "
        "We need a bit more clarity, or a teammate should review this request "
        "before drafting a final answer. "
        "A human must approve any reply before it is sent."
    )
