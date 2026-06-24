"""Integration tests for the decode HTTP API."""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import app.core.db
from app.core.auth import require_auth
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
    fastapi_app.dependency_overrides[require_auth] = lambda: None

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
    """Malformed provider output returns a persisted failed run in an ErrorEnvelope."""
    monkeypatch.setattr(settings, "fake_provider_mode", "malformed_json")

    with TestClient(fastapi_app) as client:
        response = client.post(
            "/v1/briefs/decode",
            json={"brief_text": "Build a thing."},
        )

    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "MALFORMED_OUTPUT"
    assert data["message"]
    assert data["run_id"]


def test_post_decode_schema_validation_returns_failed_run(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing-field provider output returns a persisted failed run envelope."""
    monkeypatch.setattr(settings, "fake_provider_mode", "missing_field")

    with TestClient(fastapi_app) as client:
        response = client.post(
            "/v1/briefs/decode",
            json={"brief_text": "Build a thing."},
        )

    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "SCHEMA_VALIDATION"
    assert data["message"]
    assert data["run_id"]


def test_post_decode_invalid_severity_returns_failed_run(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid severity value returns a persisted failed run in an ErrorEnvelope."""
    monkeypatch.setattr(settings, "fake_provider_mode", "invalid_severity")

    with TestClient(fastapi_app) as client:
        response = client.post(
            "/v1/briefs/decode",
            json={"brief_text": "Build a thing."},
        )

    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "SCHEMA_VALIDATION"
    assert data["message"]
    assert data["run_id"]

    # Verify the failure was persisted and the raw output is available via GET.
    run_id = data["run_id"]
    get_response = client.get(f"/v1/briefs/runs/{run_id}")
    assert get_response.status_code == 200
    run = get_response.json()
    assert run["status"] == "failed"
    assert run["error_code"] == "SCHEMA_VALIDATION"
    assert run["raw_provider_output"]


def test_post_decode_provider_error_returns_failed_run(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A provider exception returns a persisted failed run in an ErrorEnvelope."""
    monkeypatch.setattr(settings, "fake_provider_mode", "provider_error")

    with TestClient(fastapi_app) as client:
        response = client.post(
            "/v1/briefs/decode",
            json={"brief_text": "Build a thing."},
        )

    assert response.status_code == 502
    data = response.json()
    assert data["error_code"] == "PROVIDER_ERROR"
    assert data["message"]
    assert data["run_id"]


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


def test_post_decode_missing_api_key_returns_401(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing X-API-Key header returns 401 via the real auth dependency."""
    monkeypatch.setattr(settings, "api_key", "test-secret-key")
    fastapi_app.dependency_overrides.pop(require_auth, None)

    with TestClient(fastapi_app) as client:
        response = client.post(
            "/v1/briefs/decode",
            json={"brief_text": "Build a thing."},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_post_decode_invalid_api_key_returns_401(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid X-API-Key header returns 401 via the real auth dependency."""
    monkeypatch.setattr(settings, "api_key", "test-secret-key")
    fastapi_app.dependency_overrides.pop(require_auth, None)

    with TestClient(fastapi_app) as client:
        response = client.post(
            "/v1/briefs/decode",
            json={"brief_text": "Build a thing."},
            headers={"X-API-Key": "wrong-key"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_post_decode_empty_api_key_returns_401(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty X-API-Key header must not bypass authentication."""
    monkeypatch.setattr(settings, "api_key", "test-secret-key")
    fastapi_app.dependency_overrides.pop(require_auth, None)

    with TestClient(fastapi_app) as client:
        response = client.post(
            "/v1/briefs/decode",
            json={"brief_text": "Build a thing."},
            headers={"X-API-Key": ""},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_cors_preflight(monkeypatch: pytest.MonkeyPatch) -> None:
    """CORS preflight requests receive the chrome-extension allow-origin header."""
    import importlib

    from app import main as main_module

    importlib.reload(main_module)
    main_module.app.dependency_overrides[require_auth] = lambda: None

    origin = "chrome-extension://test-extension-id"
    with TestClient(main_module.app) as client:
        response = client.options(
            "/v1/briefs/decode",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin
