# api

Minimal runnable FastAPI skeleton.

## Setup

This project uses [uv](https://docs.astral.sh/uv/) for Python packaging.

```bash
uv sync --extra dev
```

## Run

```bash
uvicorn app.main:app --reload
```

The health endpoint is available at:

```bash
curl http://localhost:8000/health
```

## Test

```bash
uv run pytest
```

## Lint

```bash
uv run ruff check app tests
uv run ruff format app tests
```
