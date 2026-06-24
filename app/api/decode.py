"""HTTP routes for brief decoding."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.exceptions import APIError
from app.models.decode_run import DecodeRun
from app.schemas.brief_decode import BriefDecodeRequest, BriefDecodeResult, RunDTO
from app.services.decode_service import decode_brief

router = APIRouter(prefix="/v1/briefs", tags=["briefs"])


def _run_to_dto(run: DecodeRun) -> RunDTO:
    """Convert a terminal ``DecodeRun`` into its public ``RunDTO`` representation."""
    assert run.updated_at is not None, "terminal runs must have an updated_at timestamp"
    structured_result = (
        BriefDecodeResult.model_validate(run.structured_result)
        if run.structured_result is not None
        else None
    )
    return RunDTO(
        run_id=run.run_id,
        status=run.status,  # type: ignore[arg-type]
        input_text=run.input_text,
        structured_result=structured_result,
        raw_provider_output=run.raw_provider_output,
        error_code=run.error_code,
        error_message=run.error_message,
        created_at=run.created_at.isoformat(),
        updated_at=run.updated_at.isoformat(),
    )


@router.post("/decode", response_model=RunDTO)
async def decode(
    request: BriefDecodeRequest,
    session: AsyncSession = Depends(get_db),
) -> RunDTO:
    """Decode a raw brief into a structured result."""
    run = await decode_brief(session, request.brief_text)
    return _run_to_dto(run)


@router.get("/runs/{run_id}", response_model=RunDTO)
async def get_run(
    run_id: str,
    session: AsyncSession = Depends(get_db),
) -> RunDTO:
    """Retrieve a previously created decode run by ID."""
    run = await session.get(DecodeRun, run_id)
    if run is None:
        raise APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="RUN_NOT_FOUND",
            message=f"Run {run_id} not found",
        )
    if run.status not in {"succeeded", "failed"}:
        raise APIError(
            status_code=status.HTTP_409_CONFLICT,
            error_code="RUN_PENDING",
            message=f"Run {run_id} is still pending",
            run_id=run.run_id,
        )
    return _run_to_dto(run)
