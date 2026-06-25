"""Tests for shared + task-specific prompt composition."""

from app.services.prompts import (
    BASE_SYSTEM_PROMPT,
    build_brief_decode_prompt,
    compose_system_prompt,
)


def test_compose_prepends_base_and_appends_example() -> None:
    composed = compose_system_prompt("DO THE TASK", {"field": "value"})
    assert composed.startswith(BASE_SYSTEM_PROMPT)
    assert "DO THE TASK" in composed
    assert '"field": "value"' in composed
    assert "Example output:" in composed


def test_compose_without_example_omits_example_section() -> None:
    composed = compose_system_prompt("DO THE TASK")
    assert "Example output:" not in composed
    assert composed.startswith(BASE_SYSTEM_PROMPT)


def test_brief_decode_prompt_describes_schema_and_requests_json() -> None:
    prompt = build_brief_decode_prompt()
    # Shared base is included.
    assert BASE_SYSTEM_PROMPT in prompt
    # JSON mode requires the word JSON to appear in the prompt.
    assert "JSON" in prompt
    # Every BriefDecodeResult field is described.
    for field in (
        "summary",
        "goals",
        "deliverables",
        "constraints",
        "risks",
        "clarifying_questions",
        "recommended_next_action",
    ):
        assert field in prompt
    # The severity enum is pinned and an example is embedded.
    assert "low" in prompt and "medium" in prompt and "high" in prompt
    assert "Example output:" in prompt
