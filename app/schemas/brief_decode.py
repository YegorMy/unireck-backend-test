"""Pydantic schemas and structured-output validation for brief decoding."""

import json
from typing import Literal

from pydantic import BaseModel, Field, ValidationError


class Risk(BaseModel):
    """A risk identified while decoding a brief."""

    risk: str
    severity: Literal["low", "medium", "high"]
    reason: str


class BriefDecodeResult(BaseModel):
    """Structured output produced by the LLM for a brief."""

    summary: str
    goals: list[str]
    deliverables: list[str]
    constraints: list[str]
    risks: list[Risk]
    clarifying_questions: list[str]
    recommended_next_action: str


class BriefDecodeRequest(BaseModel):
    """Inbound request to decode a brief."""

    brief_text: str = Field(..., min_length=1)


class RunDTO(BaseModel):
    """Public representation of a decode run."""

    run_id: str
    status: Literal["succeeded", "failed"]
    input_text: str
    structured_result: BriefDecodeResult | None
    raw_provider_output: str | None
    error_code: str | None
    error_message: str | None
    created_at: str
    updated_at: str | None


class ErrorEnvelope(BaseModel):
    """Safe error response returned to clients."""

    error_code: Literal["MALFORMED_OUTPUT", "SCHEMA_VALIDATION", "PROVIDER_ERROR"]
    message: str
    run_id: str | None = None


class StructuredOutputError(Exception):
    """Raised when LLM structured output fails validation.

    The service layer maps this to the appropriate HTTP status and
    ``ErrorEnvelope`` response.
    """

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


def validate_structured_output(raw: str) -> BriefDecodeResult:
    """Parse and validate raw LLM output into ``BriefDecodeResult``.

    Args:
        raw: The raw JSON string returned by the provider.

    Returns:
        A validated ``BriefDecodeResult``.

    Raises:
        StructuredOutputError: If the output is malformed JSON or fails schema
            validation. ``error_code`` is ``MALFORMED_OUTPUT`` or
            ``SCHEMA_VALIDATION`` respectively.
    """
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        msg = f"Provider output is not valid JSON: {exc.msg}"
        raise StructuredOutputError("MALFORMED_OUTPUT", msg) from exc

    try:
        return BriefDecodeResult.model_validate(parsed)
    except ValidationError as exc:
        errors = exc.errors()
        if errors:
            first = errors[0]
            loc = ".".join(str(part) for part in first.get("loc", ()))
            reason = first.get("msg", "validation failed")
            message = f"Schema validation failed: {loc} - {reason}"
        else:
            message = "Schema validation failed"
        raise StructuredOutputError("SCHEMA_VALIDATION", message) from exc
