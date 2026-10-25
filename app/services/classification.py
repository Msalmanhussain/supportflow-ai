"""Customer message classification via local Ollama (no order DB access)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from app.schemas.classification import (
    CLASSIFICATION_JSON_SCHEMA,
    MessageClassificationResponse,
)
from app.services.ollama_client import (
    OllamaClient,
    OllamaInvalidOutputError,
    get_ollama_client,
)

PROMPT_VERSION = "classification_v1"
_PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / f"{PROMPT_VERSION}.txt"

# Application policy: never trust the model alone for these intents.
_FORCE_REVIEW_INTENTS = frozenset({"refund_request", "other"})


def load_classification_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def apply_review_policy(
    result: MessageClassificationResponse,
) -> MessageClassificationResponse:
    """Enforce human-review rules in application code (not model confidence)."""
    if result.intent in _FORCE_REVIEW_INTENTS and not result.requires_human_review:
        return result.model_copy(update={"requires_human_review": True})
    return result


def normalize_order_id(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    cleaned = raw.strip()
    return cleaned or None


async def classify_message(
    message: str,
    *,
    client: Optional[OllamaClient] = None,
) -> MessageClassificationResponse:
    """Classify a customer message. Does not query orders or send replies."""
    from app.config import get_settings

    settings = get_settings()
    if settings.allows_inference_fixture:
        from app.services.inference_fixture import classify_with_fixture

        return apply_review_policy(classify_with_fixture(message))

    ollama = client or get_ollama_client()
    system_prompt = load_classification_prompt()
    # Wrap untrusted customer text so the model treats it as data.
    user_content = (
        "Classify the following customer message.\n"
        "----- BEGIN CUSTOMER MESSAGE (UNTRUSTED DATA) -----\n"
        f"{message}\n"
        "----- END CUSTOMER MESSAGE -----"
    )

    raw = await ollama.chat_json(
        system_prompt=system_prompt,
        user_content=user_content,
        json_schema=CLASSIFICATION_JSON_SCHEMA,
    )

    if "order_id" in raw:
        raw = {**raw, "order_id": normalize_order_id(raw.get("order_id"))}

    try:
        parsed = MessageClassificationResponse.model_validate(raw)
    except ValidationError as exc:
        raise OllamaInvalidOutputError(
            "Ollama output failed schema validation."
        ) from exc

    return apply_review_policy(parsed)
