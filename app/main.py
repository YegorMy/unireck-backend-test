"""FastAPI application entrypoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Bootstrap schema on startup when explicitly enabled."""
    if settings.auto_create_tables and settings.database_url:
        await init_db()
    yield


app = FastAPI(title=settings.project_name, lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    """Return a basic health check response."""
    return {"status": "ok"}
