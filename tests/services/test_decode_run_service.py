"""Tests for the decode run persistence service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.decode_run import DecodeRun
from app.services.decode_run_service import (
    RUN_STATUS_FAILURE,
    RUN_STATUS_PENDING,
    RUN_STATUS_SUCCESS,
    create_decode_run,
    save_failure,
    save_success,
)


def _async_session_mock() -> MagicMock:
    """Return a MagicMock whose async DB methods are AsyncMocks."""
    session = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.get = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_create_decode_run_persists_pending_run() -> None:
    """create_decode_run should add a pending run and commit."""
    session = _async_session_mock()

    run = await create_decode_run(session, "Build a login API.")

    assert isinstance(run, DecodeRun)
    assert run.status == RUN_STATUS_PENDING
    assert run.input_text == "Build a login API."
    session.add.assert_called_once_with(run)
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(run)


@pytest.mark.asyncio
async def test_create_decode_run_uses_provided_id() -> None:
    """create_decode_run should use the supplied run_id when provided."""
    session = _async_session_mock()

    run = await create_decode_run(session, "input", run_id="custom-id")

    assert run.run_id == "custom-id"


@pytest.mark.asyncio
async def test_save_success_updates_run() -> None:
    """save_success should mark a run successful and store outputs."""
    session = _async_session_mock()
    existing = DecodeRun(status=RUN_STATUS_PENDING, input_text="input")
    session.get.return_value = existing

    result = await save_success(
        session,
        existing.run_id,
        {"summary": "summary"},
        "raw-llm-output",
    )

    assert result is existing
    assert result.status == RUN_STATUS_SUCCESS
    assert result.structured_result == {"summary": "summary"}
    assert result.raw_provider_output == "raw-llm-output"
    assert result.updated_at is not None
    assert result.updated_at <= datetime.now(UTC)
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(existing)


@pytest.mark.asyncio
async def test_save_success_missing_run_raises() -> None:
    """save_success should raise when the run_id does not exist."""
    session = _async_session_mock()
    session.get.return_value = None

    with pytest.raises(ValueError, match="not found"):
        await save_success(session, "missing", {"summary": "x"}, "raw")


@pytest.mark.asyncio
async def test_save_failure_updates_run() -> None:
    """save_failure should mark a run failed and store error details."""
    session = _async_session_mock()
    existing = DecodeRun(status=RUN_STATUS_PENDING, input_text="input")
    session.get.return_value = existing

    result = await save_failure(session, existing.run_id, "E_CODE", "Something failed.")

    assert result is existing
    assert result.status == RUN_STATUS_FAILURE
    assert result.error_code == "E_CODE"
    assert result.error_message == "Something failed."
    assert result.updated_at is not None
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_save_failure_missing_run_raises() -> None:
    """save_failure should raise when the run_id does not exist."""
    session = _async_session_mock()
    session.get.return_value = None

    with pytest.raises(ValueError, match="not found"):
        await save_failure(session, "missing", "E_CODE", "msg")
