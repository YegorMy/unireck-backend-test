"""Integration tests for the decode HTTP API."""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import app.core.db
from app.core.config import settings
from app.core.db import get_db, init_db
from app.main import app as fastapi_app


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Provide a fresh in-memory SQLite session for a test."""
    original_url = settings.database_url
    settings.database_url = "sqlite+aiosqlite:///:memory:"
    app.core.db._engine = None
    app.core.db._session_maker = None

    await init_db()
    session_maker = async_sessionmaker(
        app.core.db._ensure_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_maker() as session:
        fastapi_app.dependency_overrides[get_db] = lambda: session
        yield session

    fastapi_app.dependency_overrides.clear()
    settings.database_url = original_url
    app.core.db._engine = None
    app.core.db._session_maker = None


def test_post_decode_returns_run_dto(db_session: AsyncSession) -> None:
    """POST /v1/briefs/decode should return a terminal RunDTO."""
    with TestClient(fastapi_app) as client:
        response = client.post(
            "/v1/briefs/decode",
            json={"brief_text": "Build a login API."},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "succeeded"
    assert data["input_text"] == "Build a login API."
    assert data["structured_result"] is not None
    assert data["run_id"]
    assert data["created_at"]
    assert data["updated_at"]


def test_post_decode_malformed_output_returns_failed_run(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid provider output should still produce a failed RunDTO."""
    monkeypatch.setattr(settings, "fake_provider_mode", "malformed_json")

    with TestClient(fastapi_app) as client:
        response = client.post(
            "/v1/briefs/decode",
            json={"brief_text": "Build a thing."},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert data["error_code"] == "MALFORMED_OUTPUT"
    assert data["error_message"]


def test_post_decode_schema_validation_returns_failed_run(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Provider output that fails schema validation should produce a failed RunDTO."""
    monkeypatch.setattr(settings, "fake_provider_mode", "missing_field")

    with TestClient(fastapi_app) as client:
        response = client.post(
            "/v1/briefs/decode",
            json={"brief_text": "Build a thing."},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert data["error_code"] == "SCHEMA_VALIDATION"
    assert data["error_message"]


def test_post_decode_provider_error_returns_failed_run(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A provider exception should be persisted as a failed RunDTO."""
    monkeypatch.setattr(settings, "fake_provider_mode", "provider_error")

    with TestClient(fastapi_app) as client:
        response = client.post(
            "/v1/briefs/decode",
            json={"brief_text": "Build a thing."},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert data["error_code"] == "PROVIDER_ERROR"


def test_get_run_returns_run_dto(db_session: AsyncSession) -> None:
    """GET /v1/briefs/runs/{run_id} should return the existing RunDTO."""
    with TestClient(fastapi_app) as client:
        post_response = client.post(
            "/v1/briefs/decode",
            json={"brief_text": "Build a thing."},
        )
        run_id = post_response.json()["run_id"]
        get_response = client.get(f"/v1/briefs/runs/{run_id}")

    assert get_response.status_code == 200
    data = get_response.json()
    assert data["run_id"] == run_id
    assert data["status"] == "succeeded"


def test_get_run_not_found(db_session: AsyncSession) -> None:
    """GET /v1/briefs/runs/{run_id} should return an error envelope for unknown runs."""
    with TestClient(fastapi_app) as client:
        response = client.get("/v1/briefs/runs/does-not-exist")

    assert response.status_code == 404
    data = response.json()
    assert data["error_code"] == "RUN_NOT_FOUND"
    assert data["message"]


def test_cors_preflight(monkeypatch: pytest.MonkeyPatch) -> None:
    """CORS preflight requests receive the configured allow-origin header."""
    monkeypatch.setattr(settings, "cors_allow_origins", "http://test.local")

    import importlib

    from app import main as main_module

    importlib.reload(main_module)

    with TestClient(main_module.app) as client:
        response = client.options(
            "/v1/briefs/decode",
            headers={
                "Origin": "http://test.local",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://test.local"
