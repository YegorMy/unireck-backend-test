# api

Minimal runnable FastAPI skeleton.

## Setup

This project uses [uv](https://docs.astral.sh/uv/) for Python packaging.

```bash
uv sync --extra dev
```

## Configuration

All settings are read from the environment (and an optional `.env` file) and
validated against a single schema in `app/core/config.py`. Every variable uses
the `API_` prefix. Copy the documented example and adjust:

```bash
cp .env.example .env
```

Real environment variables take precedence over `.env` entries. `.env` is
gitignored; only `.env.example` is committed.

### LLM provider

`API_LLM_PROVIDER` selects the decode backend:

- `fake` (default) — a steerable canned provider; runs with **no API key**.
  Steer its output with `API_FAKE_PROVIDER_MODE`.
- `kimi` — the real [Moonshot/Kimi](https://platform.moonshot.ai/) API
  (OpenAI-compatible). Set `API_KIMI_API_KEY` and optionally `API_KIMI_MODEL`
  (default `moonshot-v1-8k`). The provider calls the chat-completions endpoint
  in JSON mode and the response is validated against the same schema as the
  fake provider.

```bash
# switch to the real provider
export API_LLM_PROVIDER=kimi
export API_KIMI_API_KEY=sk-...
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
