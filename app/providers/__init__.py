"""Provider factory and public exports."""

from typing import Literal

from app.core.config import settings
from app.providers.base import LLMProvider
from app.providers.fake import FakeProvider

ProviderName = Literal["fake", "openai"]


def get_llm_provider() -> LLMProvider:
    """Return an LLM provider instance based on application settings.

    Uses ``settings.llm_provider`` (default ``fake``).
    """
    name = settings.llm_provider
    if name == "fake":
        return FakeProvider()
    if name == "openai":
        msg = "OpenAI provider is not implemented yet"
        raise NotImplementedError(msg)
    raise ValueError(f"Unsupported LLM_PROVIDER: {name!r}")


__all__ = ["LLMProvider", "FakeProvider", "get_llm_provider"]
