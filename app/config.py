"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Secrets must come from the environment, not the image."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = Field(default="SupportFlow AI", validation_alias="APP_NAME")
    app_env: Literal["development", "test", "acceptance", "production"] = Field(
        default="development",
        validation_alias="APP_ENV",
    )
    database_url: str = Field(validation_alias="DATABASE_URL")

    # Deterministic inference fixtures — default off. Allowed only when APP_ENV
    # is test or acceptance. Startup fails if enabled in development/production.
    # Never toggled by request headers, query params, or message text.
    inference_fixture: bool = Field(
        default=False,
        validation_alias="INFERENCE_FIXTURE",
    )

    # --- Ollama (Phase 2.1). AI is NOT required for /ready. ---
    # In Docker Compose use http://host.docker.internal:11434
    # On the host use http://127.0.0.1:11434
    ollama_base_url: str = Field(
        default="http://host.docker.internal:11434",
        validation_alias="OLLAMA_BASE_URL",
    )
    ollama_model: str = Field(
        default="qwen3:1.7b",
        validation_alias="OLLAMA_MODEL",
    )
    ollama_connect_timeout_seconds: float = Field(
        default=5.0,
        validation_alias="OLLAMA_CONNECT_TIMEOUT_SECONDS",
        gt=0,
    )
    ollama_inference_timeout_seconds: float = Field(
        default=60.0,
        validation_alias="OLLAMA_INFERENCE_TIMEOUT_SECONDS",
        gt=0,
    )
    ollama_num_ctx: int = Field(
        default=2048,
        validation_alias="OLLAMA_NUM_CTX",
        ge=256,
        le=8192,
    )
    ollama_num_predict: int = Field(
        default=128,
        validation_alias="OLLAMA_NUM_PREDICT",
        ge=16,
        le=512,
    )
    ollama_max_concurrency: int = Field(
        default=1,
        validation_alias="OLLAMA_MAX_CONCURRENCY",
        ge=1,
        le=4,
    )
    ollama_temperature: float = Field(
        default=0.0,
        validation_alias="OLLAMA_TEMPERATURE",
        ge=0.0,
        le=1.0,
    )

    @field_validator("app_env", mode="before")
    @classmethod
    def normalize_app_env(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @model_validator(mode="after")
    def reject_fixture_outside_test_acceptance(self) -> Self:
        """Fail startup when INFERENCE_FIXTURE is set in development/production."""
        if self.inference_fixture and self.app_env not in {"test", "acceptance"}:
            raise ValueError(
                "INFERENCE_FIXTURE=true is only allowed when APP_ENV is "
                "'test' or 'acceptance'. Refusing to start in "
                f"APP_ENV={self.app_env!r}."
            )
        return self

    @property
    def allows_seeding(self) -> bool:
        return self.app_env in {"development", "test", "acceptance"}

    @property
    def allows_inference_fixture(self) -> bool:
        """True only when fixture flag is on and APP_ENV is test/acceptance."""
        return self.inference_fixture and self.app_env in {"test", "acceptance"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
