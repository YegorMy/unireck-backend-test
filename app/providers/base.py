"""Abstract base / protocol for LLM providers."""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract interface for brief-decoding LLM providers."""

    @abstractmethod
    async def decode(self, brief_text: str) -> str:
        """Decode ``brief_text`` into raw structured-output JSON.

        Args:
            brief_text: The raw brief text to decode.

        Returns:
            Raw JSON string from the provider.
        """
        ...
