"""Tests for the consolidated Settings schema and .env parsing."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings

_ENV_KEYS = (
    "API_PROJECT_NAME",
    "API_LLM_PROVIDER",
    "API_FAKE_PROVIDER_MODE",
    "API_API_KEY",
)


def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove API_ variables so the test sees only the .env file."""
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_env_file_is_parsed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Values are loaded from a .env file in the working directory."""
    _clear_env(monkeypatch)
    (tmp_path / ".env").write_text(
        "API_PROJECT_NAME=from-dotenv\n"
        "API_LLM_PROVIDER=fake\n"
        "API_FAKE_PROVIDER_MODE=invalid_severity\n"
        "API_API_KEY=dotenv-secret\n"
    )
    monkeypatch.chdir(tmp_path)

    settings = Settings()

    assert settings.project_name == "from-dotenv"
    assert settings.fake_provider_mode == "invalid_severity"
    assert settings.api_key == "dotenv-secret"


def test_real_env_overrides_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A real environment variable wins over the .env file entry."""
    _clear_env(monkeypatch)
    (tmp_path / ".env").write_text("API_LLM_PROVIDER=fake\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("API_LLM_PROVIDER", "openai")

    settings = Settings()

    assert settings.llm_provider == "openai"


def test_invalid_llm_provider_is_rejected() -> None:
    """An unknown provider name fails schema validation."""
    with pytest.raises(ValidationError):
        Settings(llm_provider="bogus")  # type: ignore[arg-type]


def test_invalid_fake_provider_mode_is_rejected() -> None:
    """An unknown fake-provider mode fails schema validation."""
    with pytest.raises(ValidationError):
        Settings(fake_provider_mode="nope")  # type: ignore[arg-type]
