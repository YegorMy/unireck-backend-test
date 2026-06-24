"""Exception handling for the FastAPI application."""

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from app.schemas.brief_decode import ErrorEnvelope

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Application exception with a public HTTP representation."""

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        run_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.run_id = run_id


def _build_error_response(
    status_code: int,
    error_code: str,
    message: str,
    run_id: str | None,
) -> JSONResponse:
    """Serialize an ``ErrorEnvelope`` into a JSON response."""
    envelope = ErrorEnvelope(
        error_code=error_code,  # type: ignore[arg-type]
        message=message,
        run_id=run_id,
    )
    return JSONResponse(
        status_code=status_code,
        content=envelope.model_dump(mode="json"),
    )


async def api_exception_handler(_request: Request, exc: APIError) -> JSONResponse:
    """Return an ``ErrorEnvelope`` for known application errors."""
    return _build_error_response(
        exc.status_code,
        exc.error_code,
        exc.message,
        exc.run_id,
    )


async def catch_all_exception_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """Log unhandled exceptions and return a safe ``ErrorEnvelope``."""
    logger.exception("Unhandled exception: %s", exc)
    return _build_error_response(
        500,
        "UNEXPECTED_ERROR",
        "An unexpected error occurred",
        None,
    )
