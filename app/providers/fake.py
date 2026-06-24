"""Steerable fake LLM provider for tests and local development."""

import json
import os
from typing import Literal, cast

from app.providers.base import LLMProvider

FakeProviderMode = Literal[
    "valid",
    "malformed_json",
    "missing_field",
    "invalid_severity",
    "provider_error",
]

_ENV_MODE = "FAKE_PROVIDER_MODE"


class FakeProviderError(Exception):
    """Raised when ``FakeProvider`` is configured to simulate a provider error."""


class FakeProvider(LLMProvider):
    """Steerable fake provider that returns predetermined outputs.

    The mode can be set via the constructor or the ``FAKE_PROVIDER_MODE``
    environment variable. Constructor value takes precedence.
    """

    _VALID_OUTPUT = {
        "summary": "Build a concise project brief decoder.",
        "goals": ["Extract goals", "Identify deliverables"],
        "deliverables": ["Decoded brief JSON"],
        "constraints": ["No external API key required"],
        "risks": [
            {
                "risk": "Scope creep",
                "severity": "medium",
                "reason": "Briefs can be open-ended",
            },
        ],
        "clarifying_questions": ["What is the target audience?"],
        "recommended_next_action": "Validate the structured output schema.",
    }

    _MODES: set[FakeProviderMode] = {
        "valid",
        "malformed_json",
        "missing_field",
        "invalid_severity",
        "provider_error",
    }

    def __init__(self, mode: FakeProviderMode | None = None) -> None:
        resolved = mode or os.getenv(_ENV_MODE, "valid")
        if resolved not in self._MODES:
            msg = f"Invalid fake provider mode: {resolved!r}"
            raise ValueError(msg)
        self.mode: FakeProviderMode = cast(FakeProviderMode, resolved)

    async def decode(self, brief_text: str) -> str:
        """Return a canned response according to ``self.mode``."""
        if self.mode == "valid":
            return json.dumps(self._VALID_OUTPUT)
        if self.mode == "malformed_json":
            return "this is not json"
        if self.mode == "missing_field":
            missing = dict(self._VALID_OUTPUT)
            missing.pop("summary")
            return json.dumps(missing)
        if self.mode == "invalid_severity":
            invalid = dict(self._VALID_OUTPUT)
            invalid["risks"] = [
                {
                    "risk": "Scope creep",
                    "severity": "critical",
                    "reason": "Bad value",
                },
            ]
            return json.dumps(invalid)
        if self.mode == "provider_error":
            msg = "Simulated provider error"
            raise FakeProviderError(msg)
        raise ValueError(self.mode)  # pragma: no cover
