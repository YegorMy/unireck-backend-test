"""Orchestration service for brief decoding."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.decode_run import DecodeRun
from app.providers import get_llm_provider
from app.providers.base import ProviderError
from app.schemas.brief_decode import StructuredOutputError, validate_structured_output
from app.services.decode_run_service import (
    create_decode_run,
    save_failure,
    save_success,
)

logger = logging.getLogger(__name__)


class DecodeFailedError(Exception):
    """Raised when a decode run terminates with a persisted failure.

    Carries the public error envelope fields so the API layer can map the
    failure to the correct HTTP status without leaking provider internals.
    """

    def __init__(
        self,
        run_id: str,
        error_code: str,
        message: str,
    ) -> None:
        super().__init__(message)
        self.run_id = run_id
        self.error_code = error_code
        self.message = message


async def decode_brief(session: AsyncSession, brief_text: str) -> DecodeRun:
    """Create a decode run, invoke the LLM provider, validate output, and persist.

    Args:
        session: Database session for persistence.
        brief_text: Raw brief text to decode.

    Returns:
        The terminal ``DecodeRun`` after the provider result has been saved.
    """
    run = await create_decode_run(session, brief_text)
    provider = get_llm_provider()

    try:
        raw_output = await provider.decode(brief_text)
        structured = validate_structured_output(raw_output)
    except StructuredOutputError as exc:
        run = await save_failure(session, run.run_id, exc.error_code, exc.message)
        run.raw_provider_output = raw_output
        await session.commit()
        await session.refresh(run)
        raise DecodeFailedError(run.run_id, exc.error_code, exc.message) from exc
    except ProviderError as exc:
        logger.exception("LLM provider request failed for run %s", run.run_id)
        run = await save_failure(
            session,
            run.run_id,
            "PROVIDER_ERROR",
            "LLM provider request failed",
        )
        raise DecodeFailedError(
            run.run_id,
            "PROVIDER_ERROR",
            "LLM provider request failed",
        ) from exc
    except Exception:
        logger.exception("Unexpected error during decode for run %s", run.run_id)
        run = await save_failure(
            session,
            run.run_id,
            "PROVIDER_ERROR",
            "Unexpected error during decode",
        )
        raise
    else:
        run = await save_success(
            session,
            run.run_id,
            structured.model_dump(mode="json"),
            raw_output,
        )

    return run
