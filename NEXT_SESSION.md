# Next Session — Pick Up Here

## Project

AI Agent Memory System — FastAPI REST API for AI agent long-term memory.
SQLite (structured data) + Qdrant (vector embeddings), two-phase sync pattern.

Run tests: `source .venv/bin/activate && pytest tests/ -v`
Run app: `PYTHONPATH=src uvicorn main:app --reload`

---

## Status: COMPLETE

The entire application is built and all 77 tests pass (40 service + 37 API).

```
pytest tests/ -v
# 77 passed
```

---

## What is complete

### Infrastructure
- `src/app/core/config.py` — Settings via pydantic-settings
- `src/app/models/database.py` — ORM models (Note, BufferNote, Tag, NoteTag, Link, RelationType, Metadata)
- `src/app/models/enums.py` — SearchType enum
- `src/app/models/schemas.py` — All Pydantic request/response schemas
- `src/app/db/session.py` — SQLAlchemy session + `init_db()`
- `src/app/db/qdrant.py` — Qdrant client + `init_qdrant()`

### Services (all in `src/app/services/`)
- `embedding_service.py`, `note_service.py`, `buffer_service.py`, `tag_service.py`
- `relation_service.py`, `link_service.py`, `search_service.py`
- `export_service.py`, `admin_service.py`

### API (all in `src/app/api/`)
- `deps.py`, `buffer.py`, `notes.py`, `tags.py`, `relations.py`, `export.py`, `admin.py`
- 39 routes total

### Tests
- `tests/conftest.py` — autouse mocks for embeddings and Qdrant
- `tests/test_services/` — 40 tests covering all service functions
- `tests/test_api/` — 37 tests covering all API endpoints

---

## Critical design notes

- **Two-phase sync**: notes written to SQLite with `synced=False`, then embedded, then `synced=True`.
- **Route ordering**: `/api/notes/search` and `/api/notes/links` MUST stay before `/{note_id}`. `/api/buffer/cleanup` MUST stay before `/api/buffer/{note_id}`.
- **Export is JSON** (not ZIP/markdown).
- **Mock all embeddings in tests** — never call real Ollama/OpenAI.
- **`Note.tags` property** — do not remove, it makes `NoteResponse.model_validate(note)` work.
- **API test conftest uses `StaticPool`** — required for SQLite in-memory with TestClient (different threads).
