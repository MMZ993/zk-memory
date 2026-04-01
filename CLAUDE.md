# CLAUDE.md — Instructions for Claude Sessions

## Project: AI Agent Memory System

A FastAPI REST API providing long-term memory for AI agents. Uses SQLite (structured data) + Qdrant (vector embeddings) with a two-phase sync pattern.

## Always Read First

1. `PROGRESS.md` — current implementation status and what to build next
2. `docs/implementation-guide.md` — step-by-step code for each phase
3. `docs/api-specification.md` — exact API endpoint specs to implement against
4. `docs/database-schema.md` — SQL schemas and SQLAlchemy models

## Project Structure

```
src/
  main.py       # FastAPI entry point
  app/
    api/        # FastAPI route handlers
    models/     # SQLAlchemy models (database.py) + Pydantic schemas (schemas.py)
    services/   # Business logic (one file per domain)
    db/         # DB clients: session.py (SQLite), qdrant.py (Qdrant)
    utils/      # markdown.py
scripts/        # Bash scripts for human operations
tests/          # test_api/, test_services/, test_utils/
docs/           # All design docs + IMPLEMENTATION_GAPS.md
```

Docker copies `src/` only — docs, tests, and config files never enter the image.

## Tech Stack

- **Python 3.13** with `uv` package manager
- **FastAPI** + uvicorn
- **SQLite** via SQLAlchemy 2.0 ORM
- **Qdrant** for vector storage (run via Docker)
- **Embeddings**: Local Ollama (`nomic-embed-text`)
- **Auth**: Optional `X-API-Key` header (set `API_KEY` env var)

## Running the Project

```bash
# Activate venv
source .venv/bin/activate

# Start Qdrant (required)
docker run -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant

# Run app (src/ must be on PYTHONPATH)
PYTHONPATH=src uvicorn main:app --reload

# Run tests (pythonpath = ["src"] is set in pyproject.toml)
pytest tests/ -v
```

## Design Philosophy

**This API is a set of primitives, not a system.** It stores, retrieves, and searches memory. All higher-level logic — deciding what to remember, when to consolidate buffer notes into permanent notes, how to manage the knowledge graph — belongs in the calling agent. This project intentionally does NOT make those decisions. Keep implementations minimal: only provide what is necessary for functioning.

## Key Design Decisions

- **Cross-DB sync**: `synced` bool on notes. Written with `synced=false` → embedded → Qdrant upsert → `synced=true`. The `false` state means "not yet embedded" (new note or prior embedding failure).
- **Embeddings**: Async, local Ollama-only
- **Search**: 4 modes — semantic (vector), keyword (SQLite FTS5), graph (relationship traversal), hybrid
- **Buffer notes**: Fast writes to SQLite only (no embedding). The API provides primitives (create, list, mark-processed, cleanup). The calling agent decides when/how to promote buffer → notes.
- **Markdown**: DB is source of truth. Export to files for human viewing; optional sync-back via scripts
- **Backup**: External. SQLite is a file — copy `data/memory.db`. Qdrant data lives in `qdrant_storage/` — copy that directory (when stopped) or use Qdrant's native snapshot API. See `docs/backup-strategy.md`.

## Implementation Rules

- Follow `docs/implementation-guide.md` phases in order
- API endpoints MUST match `docs/api-specification.md` exactly
- DB schema MUST match `docs/database-schema.md` (including the `synced` column on notes)
- Use `src/app/db/session.py` for SQLite sessions, `src/app/db/qdrant.py` for Qdrant client
- All embedding calls must be async
- Mock embeddings in tests (never call real APIs in tests)
- Update `PROGRESS.md` when phases complete

## Environment Variables

Copy `.env.example` to `.env`. Key vars:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | SQLite path (default: `sqlite:///./data/memory.db`) |
| `QDRANT_HOST` | Qdrant host (default: `localhost`) |
| `EMBEDDING_MODEL` | Local Ollama embedding model |
| `OLLAMA_HOST` | Ollama endpoint URL |
| `API_KEY` | Optional API authentication |
| `BUFFER_RETENTION_DAYS` | Days to keep processed buffer notes |

## Documentation Files

| File | When to Reference |
|------|------------------|
| `docs/database-schema.md` | Creating/modifying models |
| `docs/api-specification.md` | Implementing API routes |
| `docs/configuration.md` | Environment variables |
| `docs/project-structure.md` | Bash script specs |
| `docs/implementation-guide.md` | Step-by-step code |
| `docs/testing-plan.md` | Writing tests |
| `docs/backup-strategy.md` | External backup approach |
