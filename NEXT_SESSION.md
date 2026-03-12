# Next Session — Pick Up Here

## What's done

| Phase | Status |
|-------|--------|
| Phase 1 — project setup, config, Docker | ✅ |
| Phase 2 — DB models (SQLAlchemy), session, Qdrant client | ✅ |
| Phase 3 (partial) — enums, Pydantic schemas, embedding_service, note_service | ✅ |
| Tests infra — conftest.py with in-memory SQLite + autouse mocks | ✅ |

Key files already written:
- `src/app/core/config.py` — settings (Ollama default, nomic-embed-text, 768-dim)
- `src/app/models/database.py` — ORM models
- `src/app/models/enums.py` + `schemas.py` — Pydantic schemas
- `src/app/db/session.py` + `qdrant.py` — DB clients
- `src/app/services/embedding_service.py` — Ollama default, OpenAI stub (not tested)
- `src/app/services/note_service.py` — full CRUD + sync logic
- `tests/conftest.py` — shared fixtures (in-memory DB, mocked embeddings+Qdrant)
- `tests/test_services/test_schemas.py` — 16 tests, all green

## What to build next (in order)

### 1. `src/app/services/buffer_service.py`
CRUD for buffer notes — no embeddings, SQLite only.
Operations: create, get, list (filter by processed), mark_processed, delete, cleanup (delete old processed).
See `METHODS.md` (Buffer Notes section) for exact behavior.

### 2. `src/app/services/tag_service.py`
Get-or-create tag, list tags with usage counts, add/remove tag from note.

### 3. `src/app/services/link_service.py` + `relation_service.py`
Links between notes. Auto-create relation type if it doesn't exist.
See `METHODS.md` (Links + Relation Types sections).

### 4. `src/app/services/search_service.py`
Four modes: semantic (Qdrant), keyword (SQLite FTS5), hybrid, graph traversal.
FTS5 virtual table needs to be created in `init_db()` — not in ORM models.

### 5. `src/app/services/export_service.py`
Read-only JSON dumps. See `METHODS.md` (Export section).

### 6. API routes + wire `main.py`
One file per resource in `src/app/api/`. See `METHODS.md` for all 31 endpoints.
Add lifespan to `main.py` that calls `init_db()` + `init_qdrant()`.

### 7. Tests
Each service gets a test file in `tests/test_services/`.
Each API module gets a test file in `tests/test_api/`.

## Running tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

## Running the app

```bash
# Qdrant (keep running in background)
docker run -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant

# App
source .venv/bin/activate
PYTHONPATH=src uvicorn main:app --reload
```

## Key design rules (from CLAUDE.md)
- Always read `PROGRESS.md` + `docs/implementation-guide.md` at session start
- API endpoints must match `docs/api-specification.md` exactly
- Mock embeddings in ALL tests — never call real Ollama/OpenAI
- Two-phase sync: SQLite write (synced=false) → embed → Qdrant upsert → synced=true
- Update `PROGRESS.md` when phases complete
