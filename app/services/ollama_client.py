"""Async Ollama HTTP client (host service; FastAPI may call via host.docker.internal)."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Base error for Ollama integration (no customer message bodies logged)."""

    code: str = "ollama_error"
    status_code: int = 502

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class OllamaUnavailableError(OllamaError):
    code = "ollama_unavailable"
    status_code = 503


class OllamaModelMissingError(OllamaError):
    code = "ollama_model_missing"
    status_code = 503


class OllamaTimeoutError(OllamaError):
    code = "ollama_timeout"
    status_code = 504


class OllamaInvalidOutputError(OllamaError):
    code = "ollama_invalid_output"
    status_code = 502


class OllamaClient:
    """Thin async client with timeouts and a process-wide concurrency limit."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._semaphore = asyncio.Semaphore(self._settings.ollama_max_concurrency)
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def base_url(self) -> str:
        return self._settings.ollama_base_url.rstrip("/")

    @property
    def model(self) -> str:
        return self._settings.ollama_model

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            timeout = httpx.Timeout(
                connect=self._settings.ollama_connect_timeout_seconds,
                read=self._settings.ollama_inference_timeout_seconds,
                write=self._settings.ollama_connect_timeout_seconds,
                pool=self._settings.ollama_connect_timeout_seconds,
            )
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=timeout,
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def chat_json(
        self,
        *,
        system_prompt: str,
        user_content: str,
        json_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Call Ollama /api/chat with schema-constrained JSON (`format`).

        Uses non-thinking mode when supported (`think: false`).
        Does not log user_content (may contain customer text).
        """
        payload: dict[str, Any] = {
            "model": self.model,
            "stream": False,
            "think": False,
            "format": json_schema,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "options": {
                "temperature": self._settings.ollama_temperature,
                "num_ctx": self._settings.ollama_num_ctx,
                "num_predict": self._settings.ollama_num_predict,
            },
        }

        async with self._semaphore:
            client = await self._get_client()
            try:
                response = await client.post("/api/chat", json=payload)
            except httpx.ConnectError as exc:
                logger.warning(
                    "ollama_connect_failed base_url=%s model=%s error=%s",
                    self.base_url,
                    self.model,
                    exc.__class__.__name__,
                )
                raise OllamaUnavailableError(
                    "The local Ollama service is unavailable."
                ) from exc
            except httpx.TimeoutException as exc:
                logger.warning(
                    "ollama_timeout base_url=%s model=%s error=%s",
                    self.base_url,
                    self.model,
                    exc.__class__.__name__,
                )
                raise OllamaTimeoutError(
                    "The local model timed out while classifying the message."
                ) from exc
            except httpx.HTTPError as exc:
                logger.warning(
                    "ollama_http_error base_url=%s model=%s error=%s",
                    self.base_url,
                    self.model,
                    exc.__class__.__name__,
                )
                raise OllamaUnavailableError(
                    "The local Ollama service could not be reached."
                ) from exc

        if response.status_code == 404:
            logger.warning(
                "ollama_model_missing model=%s status=%s",
                self.model,
                response.status_code,
            )
            raise OllamaModelMissingError(
                f"Ollama model {self.model!r} is not available. Pull it on the host."
            )

        if response.status_code >= 500:
            logger.warning(
                "ollama_server_error model=%s status=%s",
                self.model,
                response.status_code,
            )
            raise OllamaUnavailableError(
                "The local Ollama service returned a server error."
            )

        if response.status_code >= 400:
            # Ollama sometimes returns 400 for unknown model names.
            body_preview = response.text[:200].lower()
            if "not found" in body_preview or "model" in body_preview:
                logger.warning(
                    "ollama_client_error_model model=%s status=%s",
                    self.model,
                    response.status_code,
                )
                raise OllamaModelMissingError(
                    f"Ollama model {self.model!r} is not available. Pull it on the host."
                )
            logger.warning(
                "ollama_client_error model=%s status=%s",
                self.model,
                response.status_code,
            )
            raise OllamaUnavailableError(
                "The local Ollama service rejected the classification request."
            )

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise OllamaInvalidOutputError(
                "Ollama returned a non-JSON envelope."
            ) from exc

        message = data.get("message") if isinstance(data, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise OllamaInvalidOutputError(
                "Ollama returned an empty classification payload."
            )

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise OllamaInvalidOutputError(
                "Ollama returned content that is not valid JSON."
            ) from exc

        if not isinstance(parsed, dict):
            raise OllamaInvalidOutputError(
                "Ollama JSON payload must be an object."
            )
        return parsed


_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    global _client
    if _client is None:
        _client = OllamaClient()
    return _client


def reset_ollama_client() -> None:
    """Test helper: drop the cached client so settings can be re-read."""
    global _client
    _client = None
