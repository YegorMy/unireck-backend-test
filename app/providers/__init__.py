"""Provider factory and public exports."""

import os
from typing import Literal

from app.providers.base import LLMProvider
from app.providers.fake import FakeProvider

ProviderName = Literal["fake", "openai"]


def get_llm_provider() -> LLMProvider:
    """Return an LLM provider instance based on environment configuration.

    Reads ``LLM_PROVIDER`` (default ``fake``) and ``FAKE_PROVIDER_MODE``
    (default ``valid``).
    """
    name = os.getenv("LLM_PROVIDER", "fake")
    if name == "fake":
        return FakeProvider()
    if name == "openai":
        msg = "OpenAI provider is not implemented yet"
        raise NotImplementedError(msg)
    raise ValueError(f"Unsupported LLM_PROVIDER: {name!r}")


__all__ = ["LLMProvider", "FakeProvider", "get_llm_provider"]
