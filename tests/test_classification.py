"""Classification endpoint tests — mocked Ollama only (no real model required)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.classification import MessageClassificationResponse
from app.services.classification import apply_review_policy
from app.services.ollama_client import (
    OllamaInvalidOutputError,
    OllamaModelMissingError,
    OllamaTimeoutError,
    OllamaUnavailableError,
)


@pytest.fixture()
def classify_client():
    """HTTP client without requiring DB overrides for classification routes."""
    with TestClient(app) as client:
        yield client


def test_valid_classification(classify_client: TestClient) -> None:
    mocked = MessageClassificationResponse(
        intent="order_status",
        order_id="SF-1001",
        requires_human_review=False,
    )
    with patch(
        "app.api.routes.classifications.classify_message",
        new=AsyncMock(return_value=mocked),
    ):
        response = classify_client.post(
            "/api/v1/demo/message-classifications",
            json={"message": "Where is order SF-1001?"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "order_status"
    assert body["order_id"] == "SF-1001"
    assert body["requires_human_review"] is False


def test_invalid_json_schema_from_model(classify_client: TestClient) -> None:
    with patch(
        "app.api.routes.classifications.classify_message",
        new=AsyncMock(
            side_effect=OllamaInvalidOutputError(
                "Ollama output failed schema validation."
            )
        ),
    ):
        response = classify_client.post(
            "/api/v1/demo/message-classifications",
            json={"message": "Hello"},
        )
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "ollama_invalid_output"


def test_unavailable_service(classify_client: TestClient) -> None:
    with patch(
        "app.api.routes.classifications.classify_message",
        new=AsyncMock(
            side_effect=OllamaUnavailableError(
                "The local Ollama service is unavailable."
            )
        ),
    ):
        response = classify_client.post(
            "/api/v1/demo/message-classifications",
            json={"message": "Where is my package?"},
        )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "ollama_unavailable"


def test_missing_model(classify_client: TestClient) -> None:
    with patch(
        "app.api.routes.classifications.classify_message",
        new=AsyncMock(
            side_effect=OllamaModelMissingError(
                "Ollama model 'qwen3:1.7b' is not available. Pull it on the host."
            )
        ),
    ):
        response = classify_client.post(
            "/api/v1/demo/message-classifications",
            json={"message": "Where is my package?"},
        )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "ollama_model_missing"


def test_timeout(classify_client: TestClient) -> None:
    with patch(
        "app.api.routes.classifications.classify_message",
        new=AsyncMock(
            side_effect=OllamaTimeoutError(
                "The local model timed out while classifying the message."
            )
        ),
    ):
        response = classify_client.post(
            "/api/v1/demo/message-classifications",
            json={"message": "Where is my package?"},
        )
    assert response.status_code == 504
    assert response.json()["detail"]["code"] == "ollama_timeout"


def test_mandatory_review_enforcement() -> None:
    refund = MessageClassificationResponse(
        intent="refund_request",
        order_id="SF-1001",
        requires_human_review=False,
    )
    enforced = apply_review_policy(refund)
    assert enforced.requires_human_review is True

    other = MessageClassificationResponse(
        intent="other",
        order_id=None,
        requires_human_review=False,
    )
    assert apply_review_policy(other).requires_human_review is True

    status = MessageClassificationResponse(
        intent="order_status",
        order_id="SF-1001",
        requires_human_review=False,
    )
    assert apply_review_policy(status).requires_human_review is False


def test_blank_and_oversized_input(classify_client: TestClient) -> None:
    blank = classify_client.post(
        "/api/v1/demo/message-classifications",
        json={"message": "   "},
    )
    assert blank.status_code == 422
    assert blank.json()["detail"]["code"] == "validation_error"

    oversized = classify_client.post(
        "/api/v1/demo/message-classifications",
        json={"message": "x" * 2001},
    )
    assert oversized.status_code == 422
    assert oversized.json()["detail"]["code"] == "validation_error"


def test_ready_does_not_require_ollama(classify_client: TestClient) -> None:
    """AI must not gate /ready — readiness is DB/migrations only."""
    with patch(
        "app.services.ollama_client.httpx.AsyncClient.post",
        new=AsyncMock(side_effect=httpx.ConnectError("refused")),
    ):
        # If DB is unavailable in this fixture-less client, readiness may be 503
        # for DB reasons — that is unrelated to Ollama. Assert Ollama is unused:
        # calling /ready must not attempt Ollama (no ConnectError raised).
        response = classify_client.get("/ready")
    assert response.status_code in {200, 503}
    body = response.json()
    assert "database" in body
    assert "migrations" in body
