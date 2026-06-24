"""Async database engine and session management."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel import SQLModel

from app.core.config import settings

_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def _ensure_engine() -> AsyncEngine:
    """Return the configured async engine, creating it on first call."""
    global _engine
    if _engine is None:
        if not settings.database_url:
            msg = "DATABASE_URL is not configured"
            raise RuntimeError(msg)
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.database_echo,
        )
    return _engine


def _ensure_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the async session factory, binding it to the engine as needed."""
    global _session_maker
    if _session_maker is None:
        _session_maker = async_sessionmaker(
            _ensure_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_maker


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield an async database session for FastAPI dependency injection."""
    session_maker = _ensure_sessionmaker()
    async with session_maker() as session:
        yield session


async def init_db() -> None:
    """Create all database tables if they do not already exist."""
    from app.models.decode_run import DecodeRun  # noqa: F401

    async with _ensure_engine().begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
