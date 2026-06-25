# api — AI Brief Decoder

Backend that turns a free-text project brief into structured JSON: it sends the
brief through an LLM provider, validates the structured output, persists the run
(success **or** failure), and returns it. It runs with **no API key** out of the
box via a steerable fake provider, and can use the real Moonshot/Kimi API.

**[English](#english) · [Русский](#русский)**

---

## English

### What it does

A FastAPI service that decodes a messy client brief into a structured object —
`summary`, `goals`, `deliverables`, `constraints`, `risks` (with severity),
`clarifying_questions`, and a `recommended_next_action`. Every decode is stored
as a **run** you can fetch later by id; failures are stored too, with a safe
error envelope (`error_code` + `message` + `run_id`) and the raw provider output
kept for debugging.

### Quick start (Docker)

The whole backend — API **and** Postgres — with one command:

```bash
docker compose up --build
```

- API: <http://localhost:8000> · health: <http://localhost:8000/health>
- Interactive docs (Swagger): <http://localhost:8000/docs>
- Out of the box it uses the **fake** provider (no API key required) and the dev
  key `dev-secret-change-me`.

To use the real Kimi provider, pass the variables before `up` (or put them in a
local `.env`):

```bash
API_LLM_PROVIDER=kimi API_KIMI_API_KEY=sk-... docker compose up --build
```

### Run locally (without Docker)

```bash
uv sync --extra dev
docker compose up -d postgres          # just the database
cp .env.example .env                   # then edit as needed
uv run uvicorn app.main:app --reload
```

### Try it

```bash
# health — public, no auth
curl localhost:8000/health

# decode a brief — needs the X-API-Key header
curl -s -X POST localhost:8000/v1/briefs/decode \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-secret-change-me' \
  -d '{"brief_text":"Build a landing page in 2 weeks for a fintech startup."}'

# fetch a run by id
curl localhost:8000/v1/briefs/runs/<run_id> -H 'X-API-Key: dev-secret-change-me'
```

### Configuration

Every setting uses the `API_` prefix and is validated against a single schema in
`app/core/config.py` (read from the environment and an optional `.env` file —
real env vars win over `.env`). `.env` is gitignored; only `.env.example` is
committed.

| Variable | Default | Purpose |
|---|---|---|
| `API_LLM_PROVIDER` | `fake` | Decode backend: `fake` or `kimi` |
| `API_API_KEY` | – | Shared secret required in the `X-API-Key` header on `/v1/briefs/*` |
| `API_DATABASE_URL` | – | Async Postgres URL (set automatically inside Docker) |
| `API_FAKE_PROVIDER_MODE` | `valid` | Steer the fake provider's output |
| `API_KIMI_API_KEY` | – | Moonshot/Kimi key (when provider is `kimi`) |
| `API_KIMI_MODEL` | `moonshot-v1-8k` | Kimi model id |
| `API_CORS_ALLOW_ORIGIN_REGEX` | – | Allowed browser origins (e.g. `chrome-extension://.*`) |

### LLM providers

- **`fake`** (default) — deterministic canned output, **no API key**. Steer it
  with `API_FAKE_PROVIDER_MODE`: `valid`, `malformed_json`, `missing_field`,
  `invalid_severity`, `provider_error` — handy for demoing each failure path.
- **`kimi`** — the real [Moonshot/Kimi](https://platform.moonshot.ai/) API
  (OpenAI-compatible, JSON mode). Set `API_KIMI_API_KEY`; default model
  `moonshot-v1-8k`. The raw response is validated against the same schema as the
  fake provider.

### Testing

```bash
uv run pytest                 # tests use SQLite + a mocked provider (no Docker, no key)
uv run ruff check app tests
uv run mypy app tests
```

### Project layout

| Path | Responsibility |
|---|---|
| `app/main.py` | App construction + router/CORS wiring + `/health` |
| `app/api/` | HTTP endpoints (transport only) |
| `app/schemas/` | Pydantic request/response models + output validation |
| `app/services/` | Decode orchestration + the shared prompt registry |
| `app/providers/` | LLM providers (`fake`, `kimi`) behind one interface |
| `app/models/` | `DecodeRun` persistence (SQLModel) |
| `app/core/` | Config, auth, database session, error envelope |

---

## Русский

### Что это

Бэкенд на FastAPI, который превращает свободный текст брифа в структурированный
JSON: `summary`, `goals`, `deliverables`, `constraints`, `risks` (с уровнем
важности), `clarifying_questions` и `recommended_next_action`. Каждый разбор
сохраняется как **run**, который можно потом получить по id; неуспешные разборы
тоже сохраняются — с безопасным конвертом ошибки (`error_code` + `message` +
`run_id`) и сохранённым «сырым» ответом провайдера для отладки.

### Быстрый старт (Docker)

Весь бэкенд — API **и** Postgres — одной командой:

```bash
docker compose up --build
```

- API: <http://localhost:8000> · health: <http://localhost:8000/health>
- Интерактивная документация (Swagger): <http://localhost:8000/docs>
- По умолчанию используется **фейковый** провайдер (ключ не нужен) и дев-ключ
  `dev-secret-change-me`.

Чтобы использовать настоящий провайдер Kimi, передайте переменные перед `up`
(или положите их в локальный `.env`):

```bash
API_LLM_PROVIDER=kimi API_KIMI_API_KEY=sk-... docker compose up --build
```

### Запуск локально (без Docker)

```bash
uv sync --extra dev
docker compose up -d postgres          # только база данных
cp .env.example .env                   # затем отредактируйте при необходимости
uv run uvicorn app.main:app --reload
```

### Как попробовать

```bash
# health — публичный, без авторизации
curl localhost:8000/health

# разобрать бриф — нужен заголовок X-API-Key
curl -s -X POST localhost:8000/v1/briefs/decode \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-secret-change-me' \
  -d '{"brief_text":"Сделать лендинг для финтех-стартапа за 2 недели."}'

# получить run по id
curl localhost:8000/v1/briefs/runs/<run_id> -H 'X-API-Key: dev-secret-change-me'
```

### Конфигурация

Все настройки используют префикс `API_` и валидируются единой схемой в
`app/core/config.py` (читаются из окружения и опционального файла `.env` —
переменные окружения имеют приоритет над `.env`). Файл `.env` в `.gitignore`,
в репозитории хранится только `.env.example`.

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `API_LLM_PROVIDER` | `fake` | Бэкенд разбора: `fake` или `kimi` |
| `API_API_KEY` | – | Секрет в заголовке `X-API-Key` для `/v1/briefs/*` |
| `API_DATABASE_URL` | – | Async-URL Postgres (в Docker задаётся автоматически) |
| `API_FAKE_PROVIDER_MODE` | `valid` | Управление выводом фейкового провайдера |
| `API_KIMI_API_KEY` | – | Ключ Moonshot/Kimi (когда провайдер `kimi`) |
| `API_KIMI_MODEL` | `moonshot-v1-8k` | Идентификатор модели Kimi |
| `API_CORS_ALLOW_ORIGIN_REGEX` | – | Разрешённые источники браузера (напр. `chrome-extension://.*`) |

### LLM-провайдеры

- **`fake`** (по умолчанию) — детерминированный заранее заданный вывод, **без
  ключа**. Управляется через `API_FAKE_PROVIDER_MODE`: `valid`, `malformed_json`,
  `missing_field`, `invalid_severity`, `provider_error` — удобно для демонстрации
  каждого сценария ошибки.
- **`kimi`** — настоящий API [Moonshot/Kimi](https://platform.moonshot.ai/)
  (совместим с OpenAI, режим JSON). Задайте `API_KIMI_API_KEY`; модель по
  умолчанию `moonshot-v1-8k`. Ответ валидируется той же схемой, что и у фейкового
  провайдера.

### Тесты

```bash
uv run pytest                 # тесты используют SQLite + мок-провайдер (без Docker и ключа)
uv run ruff check app tests
uv run mypy app tests
```

### Структура проекта

| Путь | Ответственность |
|---|---|
| `app/main.py` | Сборка приложения + подключение роутеров/CORS + `/health` |
| `app/api/` | HTTP-эндпоинты (только транспорт) |
| `app/schemas/` | Pydantic-модели запросов/ответов + валидация вывода |
| `app/services/` | Оркестрация разбора + общий реестр промптов |
| `app/providers/` | LLM-провайдеры (`fake`, `kimi`) за единым интерфейсом |
| `app/models/` | Хранение `DecodeRun` (SQLModel) |
| `app/core/` | Конфигурация, авторизация, сессия БД, конверт ошибок |
