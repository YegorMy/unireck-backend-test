"""Application settings via pydantic-settings."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

LLMProviderName = Literal["fake", "openai", "kimi"]
"""Supported ``API_LLM_PROVIDER`` values."""

FakeProviderMode = Literal[
    "valid",
    "malformed_json",
    "missing_field",
    "invalid_severity",
    "provider_error",
]
"""Steerable ``FakeProvider`` output modes (``API_FAKE_PROVIDER_MODE``)."""


class Settings(BaseSettings):
    """Application configuration parsed from the environment and a ``.env`` file.

    Every variable uses the ``API_`` prefix (e.g. ``API_DATABASE_URL``) and is
    validated against this single schema. A local ``.env`` file is read when
    present; real environment variables take precedence over ``.env`` entries.
    """

    model_config = SettingsConfigDict(
        env_prefix="API_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    project_name: str = "api"
    database_url: str = ""
    database_echo: bool = False
    llm_provider: LLMProviderName = "fake"
    fake_provider_mode: FakeProviderMode = "valid"
    kimi_api_key: str = ""
    kimi_base_url: str = "https://api.moonshot.ai/v1"
    # Fast non-thinking model, well-suited to structured extraction. The
    # thinking models (kimi-k2.6/k2.7) also work but are slower and pin
    # temperature — raise API_KIMI_TIMEOUT if you switch to one.
    kimi_model: str = "moonshot-v1-8k"
    # Optional: omitted from the request when None so each model uses its own
    # default. Some thinking models (e.g. kimi-k2.6/k2.7) only accept 1.
    kimi_temperature: float | None = None
    kimi_max_tokens: int = 2048
    kimi_timeout: float = 30.0
    api_key: str = ""
    cors_allow_origin_regex: str = ""
    cors_allow_methods: list[str] = ["GET", "POST", "OPTIONS"]
    cors_allow_headers: list[str] = ["Content-Type", "X-API-Key"]
    cors_allow_credentials: bool = False


settings = Settings()
