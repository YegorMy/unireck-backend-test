"""Tests for the fake LLM provider and factory."""

import json

import pytest

from app.providers import FakeProvider, get_llm_provider
from app.providers.base import LLMProvider
from app.providers.fake import FakeProviderError
from app.schemas.brief_decode import StructuredOutputError, validate_structured_output


class TestFakeProvider:
    async def test_valid_mode_returns_valid_json(self) -> None:
        provider = FakeProvider("valid")
        raw = await provider.decode("brief")
        parsed = json.loads(raw)
        assert parsed["summary"]
        assert parsed["goals"]
        assert parsed["risks"]

    async def test_malformed_json_mode(self) -> None:
        provider = FakeProvider("malformed_json")
        raw = await provider.decode("brief")
        with pytest.raises(StructuredOutputError, match="not valid JSON"):
            validate_structured_output(raw)

    async def test_missing_field_mode(self) -> None:
        provider = FakeProvider("missing_field")
        raw = await provider.decode("brief")
        with pytest.raises(StructuredOutputError, match="Schema validation failed"):
            validate_structured_output(raw)

    async def test_invalid_severity_mode(self) -> None:
        provider = FakeProvider("invalid_severity")
        raw = await provider.decode("brief")
        with pytest.raises(StructuredOutputError, match="Schema validation failed"):
            validate_structured_output(raw)

    async def test_provider_error_mode(self) -> None:
        provider = FakeProvider("provider_error")
        with pytest.raises(FakeProviderError, match="Simulated provider error"):
            await provider.decode("brief")

    async def test_mode_read_from_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("FAKE_PROVIDER_MODE", "malformed_json")
        provider = FakeProvider()
        raw = await provider.decode("brief")
        with pytest.raises(StructuredOutputError, match="not valid JSON"):
            validate_structured_output(raw)

    def test_invalid_mode_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid fake provider mode"):
            FakeProvider("unknown")  # type: ignore[arg-type]

    def test_is_llm_provider(self) -> None:
        provider = FakeProvider("valid")
        assert isinstance(provider, LLMProvider)


class TestProviderFactory:
    def test_default_returns_fake_provider(self) -> None:
        provider = get_llm_provider()
        assert isinstance(provider, FakeProvider)

    def test_fake_provider_mode_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "fake")
        monkeypatch.setenv("FAKE_PROVIDER_MODE", "provider_error")
        provider = get_llm_provider()
        assert isinstance(provider, FakeProvider)

    def test_unsupported_provider(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "unknown")
        with pytest.raises(ValueError, match="Unsupported LLM_PROVIDER"):
            get_llm_provider()

    def test_openai_not_implemented(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        with pytest.raises(NotImplementedError, match="not implemented yet"):
            get_llm_provider()
