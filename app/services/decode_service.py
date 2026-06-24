"""Orchestration service for brief decoding."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.decode_run import DecodeRun
from app.providers import get_llm_provider
from app.schemas.brief_decode import StructuredOutputError, validate_structured_output
from app.services.decode_run_service import (
    create_decode_run,
    save_failure,
    save_success,
)


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
    except Exception as exc:  # noqa: BLE001 - provider failures become run failures
        run = await save_failure(session, run.run_id, "PROVIDER_ERROR", str(exc))
    else:
        run = await save_success(
            session,
            run.run_id,
            structured.model_dump(mode="json"),
            raw_output,
        )

    return run
