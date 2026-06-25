"""Abstract base / protocol for LLM providers."""

from abc import ABC, abstractmethod


class ProviderError(Exception):
    """Raised when an LLM provider fails to produce a response."""


class LLMProvider(ABC):
    """Abstract, task-agnostic interface for LLM providers.

    A provider is pure transport: it sends a composed ``system_prompt`` plus the
    ``user_prompt`` to a model and returns the raw text response. Prompt
    composition (shared base + per-action overrides) lives in
    ``app.services.prompts``, and output validation lives in ``app.schemas`` —
    not here.
    """

    @abstractmethod
    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Send a system + user prompt to the model and return its raw output.

        Args:
            system_prompt: The composed system/instruction prompt for the action.
            user_prompt: The user-supplied content (e.g. a raw brief).

        Returns:
            The raw text response from the provider (typically a JSON string).
        """
        ...
