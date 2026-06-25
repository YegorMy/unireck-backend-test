"""Tests for the real Kimi (Moonshot) provider.

The external HTTP API is stubbed with ``httpx.MockTransport`` (TEST-03: mock
collaborators, never hit the real service).
"""

import json

import httpx
import pytest

from app.core.config import settings
from app.providers import KimiProvider, get_llm_provider
from app.providers.base import ProviderError

_VALID_RESULT = {
    "summary": "Decode the brief.",
    "goals": ["Extract goals"],
    "deliverables": ["JSON output"],
    "constraints": ["No key required"],
    "risks": [{"risk": "Scope creep", "severity": "medium", "reason": "Open-ended"}],
    "clarifying_questions": ["Who is the audience?"],
    "recommended_next_action": "Validate the schema.",
}


def _completion(content: str, finish_reason: str = "stop") -> dict[str, object]:
    """Build a minimal Moonshot chat-completion response envelope."""
    return {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "model": "kimi-k2.6",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": finish_reason,
            }
        ],
    }


async def test_decode_returns_content_and_sends_correct_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "kimi_api_key", "test-key")
    captured: dict[str, httpx.Request] = {}
    raw_content = json.dumps(_VALID_RESULT)

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return httpx.Response(200, json=_completion(raw_content))

    provider = KimiProvider(transport=httpx.MockTransport(handler))
    result = await provider.complete("Return JSON only.", "Build a landing page.")

    assert result == raw_content
    assert json.loads(result) == _VALID_RESULT

    request = captured["request"]
    assert str(request.url) == "https://api.moonshot.ai/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer test-key"
    body = json.loads(request.content)
    assert body["model"] == settings.kimi_model
    assert body["response_format"] == {"type": "json_object"}
    # The provider forwards the caller-composed prompts verbatim.
    assert body["messages"][0] == {"role": "system", "content": "Return JSON only."}
    assert body["messages"][1] == {"role": "user", "content": "Build a landing page."}


async def test_decode_without_api_key_raises_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "kimi_api_key", "")

    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("HTTP call must not happen without an API key")

    provider = KimiProvider(transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderError, match="not configured"):
        await provider.complete("system", "brief")


async def test_decode_raises_provider_error_on_http_error_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "kimi_api_key", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "invalid api key"}})

    provider = KimiProvider(transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderError, match="request failed"):
        await provider.complete("system", "brief")


async def test_decode_raises_provider_error_on_network_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "kimi_api_key", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    provider = KimiProvider(transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderError, match="request failed"):
        await provider.complete("system", "brief")


async def test_decode_raises_provider_error_on_malformed_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "kimi_api_key", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    provider = KimiProvider(transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderError, match="malformed response"):
        await provider.complete("system", "brief")


async def test_decode_raises_provider_error_on_non_json_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 200 with a non-JSON body (e.g. a proxy HTML page) is a provider fault."""
    monkeypatch.setattr(settings, "kimi_api_key", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=b"<html>not json</html>", headers={"content-type": "text/html"}
        )

    provider = KimiProvider(transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderError, match="malformed response"):
        await provider.complete("system", "brief")


async def test_decode_raises_provider_error_on_non_string_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "kimi_api_key", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_completion({"not": "a string"}))  # type: ignore[arg-type]

    provider = KimiProvider(transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderError, match="non-string content"):
        await provider.complete("system", "brief")


async def test_temperature_is_omitted_when_unset_and_sent_when_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Temperature is only sent when configured (thinking models reject it)."""
    monkeypatch.setattr(settings, "kimi_api_key", "test-key")
    captured: dict[str, httpx.Request] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return httpx.Response(200, json=_completion(json.dumps(_VALID_RESULT)))

    monkeypatch.setattr(settings, "kimi_temperature", None)
    await KimiProvider(transport=httpx.MockTransport(handler)).complete("s", "u")
    assert "temperature" not in json.loads(captured["request"].content)

    monkeypatch.setattr(settings, "kimi_temperature", 0.2)
    await KimiProvider(transport=httpx.MockTransport(handler)).complete("s", "u")
    assert json.loads(captured["request"].content)["temperature"] == 0.2


def test_factory_returns_kimi_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_provider", "kimi")
    assert isinstance(get_llm_provider(), KimiProvider)
