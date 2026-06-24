"""FastAPI application entrypoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.decode import router as decode_router
from app.core.config import settings
from app.core.db import init_db
from app.core.exceptions import (
    APIError,
    api_exception_handler,
    catch_all_exception_handler,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Bootstrap schema on startup when a database URL is configured."""
    if settings.database_url:
        await init_db()
    yield


app = FastAPI(title=settings.project_name, lifespan=lifespan)

if settings.cors_allow_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            origin.strip()
            for origin in settings.cors_allow_origins.split(",")
            if origin.strip()
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(decode_router)
app.add_exception_handler(APIError, api_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, catch_all_exception_handler)


@app.get("/health")
def health() -> dict[str, str]:
    """Return a basic health check response."""
    return {"status": "ok"}
