"""Unit tests for the Pydantic schemas and structured-output validator.

These tests are pure Pydantic — no database, no FastAPI app, no provider.
"""

import json

import pytest

from app.schemas.brief_decode import (
    BriefDecodeRequest,
    BriefDecodeResult,
    ErrorEnvelope,
    RunDTO,
    StructuredOutputError,
    validate_structured_output,
)


def _valid_result_dict() -> dict:
    return {
        "summary": "Build a landing page",
        "goals": ["Capture leads", "Explain the product"],
        "deliverables": ["Hero section", "Contact form"],
        "constraints": ["Must work without JS"],
        "risks": [
            {
                "risk": "Scope creep",
                "severity": "medium",
                "reason": "Stakeholders may add features",
            },
        ],
        "clarifying_questions": ["What is the launch date?"],
        "recommended_next_action": "Draft the hero copy",
    }


def test_validate_structured_output_valid() -> None:
    """A well-formed result passes validation."""
    raw = json.dumps(_valid_result_dict())

    result = validate_structured_output(raw)

    assert isinstance(result, BriefDecodeResult)
    assert result.summary == "Build a landing page"
    assert result.goals == ["Capture leads", "Explain the product"]
    assert len(result.risks) == 1
    assert result.risks[0].severity == "medium"


def test_validate_structured_output_malformed_json() -> None:
    """Non-JSON input raises MALFORMED_OUTPUT."""
    with pytest.raises(StructuredOutputError) as exc_info:
        validate_structured_output("not json at all")

    err = exc_info.value
    assert err.error_code == "MALFORMED_OUTPUT"
    assert "not valid JSON" in err.message


def test_validate_structured_output_missing_required_field() -> None:
    """A JSON object missing a required field raises SCHEMA_VALIDATION."""
    payload = _valid_result_dict()
    del payload["goals"]
    raw = json.dumps(payload)

    with pytest.raises(StructuredOutputError) as exc_info:
        validate_structured_output(raw)

    err = exc_info.value
    assert err.error_code == "SCHEMA_VALIDATION"
    assert "goals" in err.message


def test_validate_structured_output_invalid_severity() -> None:
    """An invalid severity literal raises SCHEMA_VALIDATION and names the field."""
    payload = _valid_result_dict()
    payload["risks"][0]["severity"] = "critical"
    raw = json.dumps(payload)

    with pytest.raises(StructuredOutputError) as exc_info:
        validate_structured_output(raw)

    err = exc_info.value
    assert err.error_code == "SCHEMA_VALIDATION"
    assert "severity" in err.message


def test_brief_decode_request_rejects_empty_text() -> None:
    """The request schema rejects an empty brief."""
    with pytest.raises(ValueError):
        BriefDecodeRequest(brief_text="")


def test_error_envelope_shape() -> None:
    """ErrorEnvelope carries the agreed public shape."""
    envelope = ErrorEnvelope(
        error_code="SCHEMA_VALIDATION",
        message="Schema validation failed: severity - ...",
        run_id="run-123",
    )
    assert envelope.error_code == "SCHEMA_VALIDATION"
    assert envelope.run_id == "run-123"


def test_run_dto_shape() -> None:
    """RunDTO carries the agreed public shape."""
    result = BriefDecodeResult.model_validate(_valid_result_dict())
    dto = RunDTO(
        run_id="run-123",
        status="succeeded",
        input_text="Build a landing page",
        structured_result=result,
        raw_provider_output="{}",
        error_code=None,
        error_message=None,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    assert dto.run_id == "run-123"
    assert dto.structured_result is not None
    assert dto.structured_result.summary == "Build a landing page"


def test_run_dto_rejects_invalid_status() -> None:
    """RunDTO.status is constrained to the agreed terminal statuses."""
    data = _valid_result_dict()
    payload = {
        "run_id": "run-123",
        "status": "pending",
        "input_text": "Build a landing page",
        "structured_result": data,
        "raw_provider_output": "{}",
        "error_code": None,
        "error_message": None,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": None,
    }
    with pytest.raises(ValueError):
        RunDTO.model_validate(payload)


def test_error_envelope_run_id_optional() -> None:
    """ErrorEnvelope.run_id is nullable and may be omitted."""
    envelope = ErrorEnvelope(
        error_code="SCHEMA_VALIDATION",
        message="Schema validation failed",
    )
    assert envelope.run_id is None


def test_error_envelope_rejects_invalid_error_code() -> None:
    """ErrorEnvelope.error_code is constrained to the agreed codes."""
    with pytest.raises(ValueError):
        ErrorEnvelope.model_validate(
            {
                "error_code": "UNKNOWN_CODE",
                "message": "Something went wrong",
                "run_id": "run-123",
            }
        )
