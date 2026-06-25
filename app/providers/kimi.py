"""Real Moonshot (Kimi) LLM provider.

Talks to the Moonshot/Kimi OpenAI-compatible chat-completions API
(``POST {base_url}/chat/completions``) in JSON mode and returns the raw
assistant message content. The returned string is validated downstream by
``app.schemas.brief_decode.validate_structured_output`` — this provider is a
thin transport adapter and performs no schema validation itself.
"""

import json
import logging

import httpx

from app.core.config import settings
from app.providers.base import LLMProvider, ProviderError

logger = logging.getLogger(__name__)


class KimiProvider(LLMProvider):
    """LLM provider backed by the Moonshot/Kimi chat-completions API.

    Configuration is read from :data:`app.core.config.settings`
    (``API_KIMI_*``). The optional ``transport`` argument is a dependency-
    injection seam for tests, allowing the HTTP layer to be stubbed.
    """

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._api_key = settings.kimi_api_key
        self._base_url = settings.kimi_base_url.rstrip("/")
        self._model = settings.kimi_model
        self._temperature = settings.kimi_temperature
        self._max_tokens = settings.kimi_max_tokens
        self._timeout = settings.kimi_timeout
        self._transport = transport

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Call the Kimi API in JSON mode and return the raw response content.

        Args:
            system_prompt: The composed system/instruction prompt (built by
                ``app.services.prompts``).
            user_prompt: The user-supplied content to act on.

        Raises:
            ProviderError: If the API key is missing, the request fails, the
                response is a non-success status, or the response envelope is
                malformed. The message is intentionally generic so provider
                internals are not surfaced to callers.
        """
        if not self._api_key:
            raise ProviderError("Kimi API key is not configured")

        payload: dict[str, object] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_completion_tokens": self._max_tokens,
            "response_format": {"type": "json_object"},
        }
        # Only send temperature when explicitly configured: some thinking models
        # (e.g. kimi-k2.6) reject any value other than their fixed default.
        if self._temperature is not None:
            payload["temperature"] = self._temperature
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    "/chat/completions", json=payload, headers=headers
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Kimi API returned %s for model %s",
                exc.response.status_code,
                self._model,
            )
            raise ProviderError("Kimi API request failed") from exc
        except httpx.HTTPError as exc:
            logger.warning("Kimi API request error: %s", type(exc).__name__)
            raise ProviderError("Kimi API request failed") from exc

        try:
            data = response.json()
            choice = data["choices"][0]
            content = choice["message"]["content"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            logger.warning("Kimi API returned an unexpected response envelope")
            raise ProviderError("Kimi API returned a malformed response") from exc

        if choice.get("finish_reason") == "length":
            logger.warning(
                "Kimi API response was truncated (finish_reason=length); "
                "consider raising API_KIMI_MAX_TOKENS"
            )

        if not isinstance(content, str):
            raise ProviderError("Kimi API returned non-string content")

        return content
