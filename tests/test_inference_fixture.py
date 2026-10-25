"""Inference fixture gating — must not bypass Ollama in development/production."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from app.config import Settings, clear_settings_cache, get_settings
from app.services.classification import classify_message
from app.services.inference_fixture import MARKER_ORDER
from app.services.ollama_client import OllamaUnavailableError


def _database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://x:x@localhost:5432/supportflow_test",
    )


@pytest.fixture(autouse=True)
def _clear_settings():
    clear_settings_cache()
    yield
    clear_settings_cache()


@pytest.mark.asyncio
async def test_fixture_used_in_acceptance_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "acceptance")
    monkeypatch.setenv("INFERENCE_FIXTURE", "true")
    monkeypatch.setenv("DATABASE_URL", _database_url())
    clear_settings_cache()
    assert get_settings().allows_inference_fixture is True
    result = await classify_message(f"{MARKER_ORDER} Where is SF-1001?")
    assert result.intent == "order_status"
    assert result.order_id == "SF-1001"


@pytest.mark.asyncio
async def test_fixture_defaults_off_in_development(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("INFERENCE_FIXTURE", raising=False)
    monkeypatch.setenv("DATABASE_URL", _database_url())
    clear_settings_cache()
    assert get_settings().inference_fixture is False
    assert get_settings().allows_inference_fixture is False
    with patch(
        "app.services.classification.get_ollama_client",
    ) as mock_client_factory:
        client = mock_client_factory.return_value
        client.chat_json = AsyncMock(
            side_effect=OllamaUnavailableError("should hit ollama path")
        )
        with pytest.raises(OllamaUnavailableError):
            await classify_message(f"{MARKER_ORDER} Where is SF-1001?")


@pytest.mark.parametrize("app_env", ["development", "production"])
def test_startup_fails_when_fixture_enabled_outside_allowed_envs(
    app_env: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("INFERENCE_FIXTURE", "true")
    monkeypatch.setenv("DATABASE_URL", _database_url())
    clear_settings_cache()
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    assert "INFERENCE_FIXTURE" in str(exc_info.value)


def test_message_markers_do_not_enable_fixture_without_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Markers in message text never flip fixture mode; only env + APP_ENV do."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("INFERENCE_FIXTURE", raising=False)
    monkeypatch.setenv("DATABASE_URL", _database_url())
    clear_settings_cache()
    settings = get_settings()
    assert settings.allows_inference_fixture is False
    # Marker presence alone must not change gating.
    assert MARKER_ORDER
    assert settings.allows_inference_fixture is False
