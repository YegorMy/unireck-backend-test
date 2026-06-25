"""Shared and task-specific LLM prompts.

A single :data:`BASE_SYSTEM_PROMPT` carries the rules common to every
structured-output action. Each action layers its own task instructions (and an
optional example) on top via :func:`compose_system_prompt`. This is the seam
that lets one generic provider serve many agents/actions: the provider just
transports whatever system prompt the action composes.

To add a new action, write a ``build_<action>_prompt()`` that calls
``compose_system_prompt`` with that action's instructions and example.
"""

import json
from typing import Any

BASE_SYSTEM_PROMPT = (
    "You are a precise structured-output assistant for a delivery team.\n"
    "Always return exactly ONE valid JSON object and nothing else: no prose, "
    "no markdown, no code fences.\n"
    "Ground every field strictly in the user's input; never invent unsupported "
    "facts. When information is missing, prefer empty arrays or explicit "
    "clarifying questions over guessing.\n"
    "The output must be parseable by a strict json.loads."
)


def compose_system_prompt(task_instructions: str, example: Any | None = None) -> str:
    """Compose the shared base prompt with an action's task-specific override.

    Args:
        task_instructions: The action-specific role/schema description.
        example: Optional example output object, embedded to anchor the shape.

    Returns:
        The full system prompt: shared base, then task instructions, then the
        example (when provided).
    """
    parts = [BASE_SYSTEM_PROMPT, task_instructions]
    if example is not None:
        parts.append("Example output:\n" + json.dumps(example, ensure_ascii=False))
    return "\n\n".join(parts)


_BRIEF_DECODE_TASK = (
    "Task: decode a raw, messy client project brief into a single structured "
    "JSON object a team can act on. Use exactly these fields:\n"
    "- summary (string): one or two sentences capturing the gist of the brief.\n"
    "- goals (array of strings): the outcomes the client wants.\n"
    "- deliverables (array of strings): concrete artifacts to produce.\n"
    "- constraints (array of strings): budget, deadline, tech, or scope limits.\n"
    '- risks (array of objects): each {"risk": string, "severity": one of '
    '"low" | "medium" | "high", "reason": string}.\n'
    "- clarifying_questions (array of strings): questions that de-risk the brief.\n"
    "- recommended_next_action (string): the single best next step.\n"
    "Rule: severity MUST be exactly one of low, medium, high (lowercase); every "
    "field is required (use an empty array for empty lists)."
)

# Mirrors ``BriefDecodeResult`` (see app/schemas/brief_decode.py).
_BRIEF_DECODE_EXAMPLE = {
    "summary": "Build a marketing landing page for a fintech launch.",
    "goals": ["Drive sign-ups", "Communicate the product value"],
    "deliverables": ["Responsive landing page", "Analytics integration"],
    "constraints": ["Two-week timeline", "Limited budget"],
    "risks": [
        {
            "risk": "Unclear brand guidelines",
            "severity": "medium",
            "reason": "No design system was provided.",
        }
    ],
    "clarifying_questions": ["Who is the target audience?"],
    "recommended_next_action": "Confirm brand assets and the launch date.",
}


def build_brief_decode_prompt() -> str:
    """Return the composed system prompt for the brief-decode action."""
    return compose_system_prompt(_BRIEF_DECODE_TASK, _BRIEF_DECODE_EXAMPLE)
