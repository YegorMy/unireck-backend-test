"""Tests for the decode run persistence service."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import app.core.db
from app.core.config import settings
from app.core.db import get_db, init_db
from app.models.decode_run import DecodeRun
from app.services.decode_run_service import (
    RUN_STATUS_FAILED,
    RUN_STATUS_PENDING,
    RUN_STATUS_SUCCEEDED,
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
    assert result.status == RUN_STATUS_SUCCEEDED
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
    assert result.status == RUN_STATUS_FAILED
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


@pytest.mark.asyncio
async def test_save_success_rejects_terminal_run() -> None:
    """save_success should raise when the run is already terminal."""
    session = _async_session_mock()
    existing = DecodeRun(status=RUN_STATUS_SUCCEEDED, input_text="input")
    session.get.return_value = existing

    with pytest.raises(ValueError, match="already terminal"):
        await save_success(session, existing.run_id, {"summary": "x"}, "raw")


@pytest.mark.asyncio
async def test_save_failure_rejects_terminal_run() -> None:
    """save_failure should raise when the run is already terminal."""
    session = _async_session_mock()
    existing = DecodeRun(status=RUN_STATUS_FAILED, input_text="input")
    session.get.return_value = existing

    with pytest.raises(ValueError, match="already terminal"):
        await save_failure(session, existing.run_id, "E_CODE", "msg")


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Provide an async SQLModel/SQLite session with tables created via init_db."""
    original_url = settings.database_url
    settings.database_url = "sqlite+aiosqlite:///:memory:"
    app.core.db._engine = None
    app.core.db._session_maker = None

    await init_db()
    session_maker = async_sessionmaker(
        app.core.db._ensure_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_maker() as session:
        yield session

    settings.database_url = original_url
    app.core.db._engine = None
    app.core.db._session_maker = None


@pytest.mark.asyncio
async def test_init_db_creates_tables(db_session: AsyncSession) -> None:
    """init_db should create the decode_runs table in the SQLite engine."""
    result = await db_session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='decode_runs'")
    )
    assert result.scalar_one() == "decode_runs"


@pytest.mark.asyncio
async def test_get_db_yields_async_session() -> None:
    """get_db should yield a working AsyncSession backed by init_db tables."""
    original_url = settings.database_url
    settings.database_url = "sqlite+aiosqlite:///:memory:"
    app.core.db._engine = None
    app.core.db._session_maker = None
    try:
        await init_db()

        db_gen = get_db()
        session = await anext(db_gen)
        assert isinstance(session, AsyncSession)

        result = await session.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='decode_runs'"
            )
        )
        assert result.scalar_one() == "decode_runs"

        try:
            await anext(db_gen)
        except StopAsyncIteration:
            pass
    finally:
        settings.database_url = original_url
        app.core.db._engine = None
        app.core.db._session_maker = None


@pytest.mark.asyncio
async def test_create_decode_run_sqlite_roundtrip(db_session: AsyncSession) -> None:
    """create_decode_run should insert a row readable from a fresh session."""
    run = await create_decode_run(db_session, "Build a login API.")
    await db_session.commit()
    await db_session.close()

    async with async_sessionmaker(
        app.core.db._ensure_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )() as fresh_session:
        loaded = await fresh_session.get(DecodeRun, run.run_id)
        assert loaded is not None
        assert loaded.status == RUN_STATUS_PENDING
        assert loaded.input_text == "Build a login API."
        assert loaded.structured_result is None
        assert loaded.created_at is not None


@pytest.mark.asyncio
async def test_save_success_sqlite_roundtrip(db_session: AsyncSession) -> None:
    """save_success should update and persist structured_result."""
    run = await create_decode_run(db_session, "input")
    structured = {"summary": "A login API", "goals": ["auth"]}

    await save_success(
        db_session,
        run.run_id,
        structured,
        "raw-llm-output",
    )
    await db_session.close()

    async with async_sessionmaker(
        app.core.db._ensure_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )() as fresh_session:
        loaded = await fresh_session.get(DecodeRun, run.run_id)
        assert loaded is not None
        assert loaded.status == RUN_STATUS_SUCCEEDED
        assert loaded.structured_result == structured
        assert loaded.raw_provider_output == "raw-llm-output"
        assert loaded.updated_at is not None


@pytest.mark.asyncio
async def test_save_failure_sqlite_roundtrip(db_session: AsyncSession) -> None:
    """save_failure should update and persist error details."""
    run = await create_decode_run(db_session, "input")

    await save_failure(
        db_session,
        run.run_id,
        "E_LLM_TIMEOUT",
        "The provider timed out.",
    )
    await db_session.close()

    async with async_sessionmaker(
        app.core.db._ensure_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )() as fresh_session:
        loaded = await fresh_session.get(DecodeRun, run.run_id)
        assert loaded is not None
        assert loaded.status == RUN_STATUS_FAILED
        assert loaded.error_code == "E_LLM_TIMEOUT"
        assert loaded.error_message == "The provider timed out."
        assert loaded.updated_at is not None
