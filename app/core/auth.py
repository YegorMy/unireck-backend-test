"""Authentication dependencies for FastAPI routers."""

import hmac

from fastapi import Header, HTTPException, status

from app.core.config import settings


async def require_auth(x_api_key: str | None = Header(default=None)) -> None:
    """Validate the API key header for protected endpoints.

    ``/health`` is intentionally excluded from this dependency so it can serve
    as a public liveness/readiness probe.

    Raises:
        HTTPException: 401 if the supplied key does not match the configured
            ``API_API_KEY`` value.
    """
    if x_api_key is None or not hmac.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
