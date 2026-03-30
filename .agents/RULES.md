# Rules

## Stack
- Backend: Python FastAPI service (`src/main.py`, routers in `src/app/api`, business logic in `src/app/services`)
- Data stores: SQL (SQLite/Postgres via SQLAlchemy) + Qdrant vector store
- Migrations: Alembic (`alembic/`, `alembic.ini`)
- CLI: Go + Cobra (`cli/cmd`, `cli/internal/client`)
- Testing: pytest (+ pytest-asyncio), plus Docker-based integration suites

## Versions
Exact project versions (locked/declared in repo):

- Python runtime: `3.13` (`.python-version`), `>=3.13` (`pyproject.toml`)
- Go runtime: `1.26` (`cli/go.mod`)

Python packages (from `uv.lock`):
- fastapi `0.135.1`
- uvicorn `0.41.0`
- python-multipart `0.0.22`
- sqlalchemy `2.0.48`
- alembic `1.18.4`
- qdrant-client `1.17.1`
- openai `2.28.0`
- python-dotenv `1.2.2`
- pydantic `2.12.5`
- pydantic-settings `2.13.1`
- httpx `0.28.1`
- psycopg `3.3.3`
- pytest `9.0.2`
- pytest-asyncio `1.3.0`
- black `26.3.1`
- isort `8.0.1`
- mypy `1.19.1`

Go packages:
- github.com/spf13/cobra `v1.10.2` (`cli/go.mod`)

Docs/convention lookup was verified via `find-docs` (Context7) for:
- FastAPI (`/fastapi/fastapi`)
- SQLAlchemy (`/websites/sqlalchemy_en_20_orm`)
- Pydantic (`/websites/pydantic_dev_2_12`)
- Alembic (`/sqlalchemy/alembic`)
- Qdrant Python client (`/qdrant/qdrant-client`)
- OpenAI Python (`/openai/openai-python/v2.11.0`)
- pytest (`/pytest-dev/pytest`)
- Cobra (`/websites/pkg_go_dev_github_com_spf13_cobra`)

## Project structure
- `src/main.py`: FastAPI app bootstrap, lifespan init, middleware, router registration.
- `src/app/api/`: HTTP endpoints grouped by resource (`notes.py`, `buffer.py`, `tags.py`, `relations.py`, `admin.py`, `export.py`).
- `src/app/services/`: domain/service logic, DB + embedding/vector orchestration.
- `src/app/models/`: SQLAlchemy models and Pydantic schemas.
- `src/app/db/`: database session wiring + Qdrant client init.
- `tests/test_api`, `tests/test_services`: fast unit/API tests with mocked embeddings/Qdrant.
- `tests/integration`: real HTTP/API integration tests, gated by `INTEGRATION_TESTS=1`.
- `cli/`: standalone Go CLI module (Cobra command tree + internal HTTP client).
- `alembic/`: migration history and env wiring.

## Conventions
- Python naming:
  - snake_case functions/variables.
  - Endpoint functions usually end with `_endpoint`.
  - UUIDs are string IDs across API/DB boundaries.
- Router style:
  - One `APIRouter` per resource with `/api/...` prefix.
  - Use `Depends(get_db)` + scope deps (`require_read`, `require_write`, etc.) on every route.
  - Validate query params with `Query(..., ge/le/pattern=...)`.
- Serialization:
  - Use `NoteResponse.model_validate(...).model_dump()` style where conversion is needed.
  - List endpoints return raw arrays (not wrapped objects), except explicit search/graph endpoints which return `{results,total}`.
- File organization:
  - Section separators are common and should be preserved (`# ── ... ──`).
- Go CLI style:
  - Commands named `*Cmd` and registered in `init()` with `AddCommand`.
  - Error exit path is centralized through `fatal(...)`.
  - Shared string parsing helpers kept local in command file when small.

## Libraries
- FastAPI: routing, DI (`Depends`), request/response validation, HTTPException boundaries at API layer.
- SQLAlchemy ORM: session-based CRUD and queries in services.
- Alembic: schema migration generation and upgrade flow.
- Pydantic v2: request/response schemas and validation constraints.
- Qdrant client: vector upsert/search/delete and collection management.
- OpenAI client: embedding generation only when provider is `openai`.
- httpx: integration tests and external HTTP interactions.
- Cobra: CLI command tree, flags, subcommands.

## Testing
- Framework: pytest, async tests via pytest-asyncio.
- Test folders:
  - `tests/test_api`: API contract behavior.
  - `tests/test_services`: service logic.
  - `tests/integration`: real-stack tests via Docker.
- Global testing rules from `tests/conftest.py`:
  - In-memory SQLite per test.
  - Embedding calls mocked (`generate_embedding`, `upsert_embedding`).
  - Qdrant client mocked for non-integration suites.
- Integration execution:
  - Must set `INTEGRATION_TESTS=1`.
  - Use Make targets (`test-integration`, `test-integration-postgres`, `test-integration-auth`).

## Do not
- Do not bypass auth dependency wiring on protected endpoints.
- Do not call real embedding providers or real Qdrant in unit/API tests.
- Do not change list endpoint response shapes without updating integration + CLI expectations.
- Do not introduce broad silent `except Exception` behavior in core paths.
- Do not pass request-scoped DB sessions/ORM objects into background tasks; pass IDs and create fresh session in task worker.
- Do not enforce strict auth defaults for local-only setups unless explicitly requested; local fail-open auth is acceptable in this project context.

## Open questions
- Should auth be fail-closed by default outside local/dev?
- Should async embedding jobs move to a worker queue (RQ/Celery/Arq) instead of FastAPI background tasks?
- Dependency source of truth set to `pyproject.toml` + `uv.lock` (with `uv sync` workflow); remove duplicate `requirements.txt` usage.
- Production target is local Ollama; OpenAI path is optional/legacy and not required for core operation.
- Liveness/readiness split is optional now but preferred for future Kubernetes-style deployment.
