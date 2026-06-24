"""Tests for the DecodeRun persistence model."""

from datetime import UTC, datetime
from uuid import UUID

from app.models.decode_run import DecodeRun


def test_decode_run_defaults() -> None:
    """A new DecodeRun should receive a UUID primary key and a timestamp."""
    run = DecodeRun(status="pending", input_text="Build a login API.")

    UUID(run.run_id, version=4)
    assert run.status == "pending"
    assert run.input_text == "Build a login API."
    assert run.structured_result is None
    assert run.error_code is None
    assert run.created_at <= datetime.now(UTC)


def test_decode_run_accepts_run_id() -> None:
    """A caller can supply an explicit run_id."""
    run = DecodeRun(run_id="manual-id", status="success", input_text="x")

    assert run.run_id == "manual-id"
