"""Persistence services for decode runs."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.decode_run import DecodeRun

# Non-final internal state used while a run is in progress. Final RunDTO statuses
# are RUN_STATUS_SUCCEEDED and RUN_STATUS_FAILED per the briefs contract.
RUN_STATUS_PENDING = "pending"
RUN_STATUS_SUCCEEDED = "succeeded"
RUN_STATUS_FAILED = "failed"

_TERMINAL_STATUSES = {RUN_STATUS_SUCCEEDED, RUN_STATUS_FAILED}


class RunNotFoundError(Exception):
    """Raised when a requested decode run does not exist."""


class RunPendingError(Exception):
    """Raised when a requested decode run has not reached a terminal status."""

    def __init__(self, run_id: str) -> None:
        super().__init__(f"Run {run_id} is still pending")
        self.run_id = run_id


async def get_terminal_run(
    session: AsyncSession,
    run_id: str,
) -> DecodeRun:
    """Retrieve a decode run and verify it is in a terminal status.

    Args:
        session: Database session for persistence.
        run_id: Public run identifier.

    Returns:
        The persisted ``DecodeRun``.

    Raises:
        RunNotFoundError: If no run exists for ``run_id``.
        RunPendingError: If the run exists but is not yet terminal.
    """
    run = await session.get(DecodeRun, run_id)
    if run is None:
        raise RunNotFoundError
    if run.status not in _TERMINAL_STATUSES:
        raise RunPendingError(run.run_id)
    return run


async def create_decode_run(
    session: AsyncSession,
    input_text: str,
    run_id: str | None = None,
) -> DecodeRun:
    """Persist a new decode run and return it."""
    run = DecodeRun(
        run_id=run_id,
        status=RUN_STATUS_PENDING,
        input_text=input_text,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


async def save_success(
    session: AsyncSession,
    run_id: str,
    structured_result: dict,
    raw_provider_output: str,
) -> DecodeRun:
    """Mark a run as successful and store its result."""
    run = await session.get(DecodeRun, run_id)
    if run is None:
        msg = f"DecodeRun {run_id} not found"
        raise ValueError(msg)
    if run.status in _TERMINAL_STATUSES:
        msg = f"DecodeRun {run_id} is already terminal (status={run.status})"
        raise ValueError(msg)

    run.status = RUN_STATUS_SUCCEEDED
    run.structured_result = structured_result
    run.raw_provider_output = raw_provider_output
    run.updated_at = datetime.now(UTC)
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


async def save_failure(
    session: AsyncSession,
    run_id: str,
    error_code: str,
    error_message: str,
) -> DecodeRun:
    """Mark a run as failed and store the error details."""
    run = await session.get(DecodeRun, run_id)
    if run is None:
        msg = f"DecodeRun {run_id} not found"
        raise ValueError(msg)
    if run.status in _TERMINAL_STATUSES:
        msg = f"DecodeRun {run_id} is already terminal (status={run.status})"
        raise ValueError(msg)

    run.status = RUN_STATUS_FAILED
    run.error_code = error_code
    run.error_message = error_message
    run.updated_at = datetime.now(UTC)
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run
