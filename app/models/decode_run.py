"""Persistence model for decode runs."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Column, DateTime, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class _JSONBCompat(TypeDecorator):
    """JSONB on PostgreSQL, generic JSON on other dialects (e.g. SQLite tests)."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class DecodeRun(SQLModel, table=True):
    """PostgreSQL-backed persistence model for a single decode run."""

    __tablename__ = "decode_runs"

    run_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    status: str = Field(index=True)
    input_text: str
    structured_result: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(_JSONBCompat, nullable=True),
    )
    raw_provider_output: str | None = Field(default=None)
    error_code: str | None = Field(default=None)
    error_message: str | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
