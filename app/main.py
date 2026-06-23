"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.core.config import Settings

settings = Settings()

app = FastAPI(title=settings.project_name)


@app.get("/health")
def health() -> dict[str, str]:
    """Return a basic health check response."""
    return {"status": "ok"}
