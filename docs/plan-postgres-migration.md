# Plan: PostgreSQL + Deployment Mode Options

## Decision: Support Both, Not Replace

Rather than switching permanently to PostgreSQL, support two deployment modes selected by `DATABASE_URL` prefix — no new env var needed, the URL already carries the signal:

| `DATABASE_URL` starts with | Mode | Vector backend |
|---|---|---|
| `sqlite:///` | **Simple / dev** | Qdrant (current) or sqlite-vec (future) |
| `postgresql://` | **Production** | Qdrant (distributed) or pgvector (single-node) |

This gives us a natural ladder:

```
Dev / home lab:       SQLite + Qdrant            (current — works today)
Single-node prod:     PostgreSQL + pgvector       (1 container, no Qdrant)
Distributed / k8s:   PostgreSQL + Qdrant          (separate scaling)
```

---

## What Needs to Change

### 1. `session.py` — make engine creation dialect-aware

Currently hardcodes SQLite options (`check_same_thread`, WAL pragma listener).
Must detect dialect from URL and only apply SQLite-specific settings for SQLite.

```python
is_sqlite = settings.database_url.startswith("sqlite")

engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False} if is_sqlite else {},
)

if is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragmas(conn, _):
        ...
```

### 2. `alembic/env.py` — pragma listener is SQLite-only

The `event.listen(connectable, "connect", _set_sqlite_pragmas)` call in
`run_migrations_online()` will crash on PostgreSQL.
Wrap it with a dialect check (read URL prefix before attaching).

### 3. Initial migration — FTS5 is SQLite-only

`d584390723bb_initial_schema.py` runs `CREATE VIRTUAL TABLE ... USING fts5` unconditionally.
Two options:

**Option A (preferred):** make the migration dialect-aware using `op.get_bind().dialect.name`:
- SQLite path: current FTS5 virtual table + 3 triggers
- PostgreSQL path: add `search_vector tsvector` column to `notes` + GIN index + PostgreSQL triggers to keep it updated on INSERT/UPDATE

**Option B:** split into two migration files, one per dialect.
Option A is cleaner — one migration, one history.

### 4. `search_service.py` — keyword search uses raw FTS5 SQL

`search_keyword()` runs a raw `SELECT note_id FROM notes_fts WHERE notes_fts MATCH ?`.
This is SQLite-only. Need to branch on dialect:

- **SQLite**: current FTS5 MATCH query (unchanged)
- **PostgreSQL**: `WHERE search_vector @@ plainto_tsquery('english', :q)` ordered by `ts_rank`

Best approach: detect at service call time via `db.bind.dialect.name` (or pass a flag from config).

### 5. Dependencies

Add to `pyproject.toml`:
- `psycopg2-binary` (PostgreSQL driver, or `asyncpg` if we want async)

For pgvector (Phase 2):
- `pgvector` Python package

### 6. Docker Compose — two profiles

**`docker-compose.yml`** (current, SQLite + Qdrant — unchanged for existing users)

**`docker-compose.postgres.yml`** — PostgreSQL + Qdrant (distributed):
```yaml
services:
  agents-memory:   # same image, DATABASE_URL points to postgres
  postgres:        # postgres:16-alpine
  qdrant:          # unchanged
```

**`docker-compose.simple.yml`** — PostgreSQL + pgvector (no Qdrant):
```yaml
services:
  agents-memory:   # VECTOR_BACKEND=pgvector, no Qdrant
  postgres:        # postgres:16-alpine with pgvector extension
```

---

## Phase Plan

### Phase 1 — PostgreSQL DB support ✅ COMPLETE (2026-03-14)

1. ✅ `session.py` — dialect-aware engine creation
2. ✅ `alembic/env.py` — guard pragma listener behind SQLite check
3. ✅ `alembic/versions/d584390723bb` — make FTS5 section dialect-aware; add PostgreSQL `tsvector` path
4. ✅ `search_service.py` — branch keyword search on `settings.db_backend`
5. ✅ `pyproject.toml` + `requirements.txt` — `psycopg[binary]>=3.1.0` (psycopg3, not psycopg2)
6. ✅ `docker-compose.postgres.yml` — PostgreSQL + Qdrant compose file
7. ✅ `.env.example` — `DB_BACKEND` + `postgresql+psycopg://` example (URL scheme required for psycopg3)
8. ✅ Integration tests — `docker-compose.test.postgres.yml` + `make test-integration-postgres`; 48/48 pass
9. ✅ `scripts/dev-reset-postgres.sh` — dev wipe utility

**Key decision made during implementation:** Added explicit `DB_BACKEND=sqlite|postgres` env var (rather than inferring from URL) for clarity in Docker deployments.

**Driver note:** URL must use `postgresql+psycopg://` (not `postgresql://`) to select psycopg3. Using `postgresql://` causes SQLAlchemy to look for the old `psycopg2` package.

### Phase 2 — pgvector as Qdrant alternative (separate branch)

Adds `VECTOR_BACKEND=qdrant|pgvector` env var.

1. `config.py` — add `vector_backend: str = "qdrant"`
2. New `src/app/db/pgvector.py` — pgvector client matching Qdrant client interface
3. `embedding_service.py` — route upsert/search through backend abstraction
4. `docker-compose.simple.yml` — PostgreSQL + pgvector, no Qdrant (true 1-image setup)
5. Alembic migration — add `embedding vector(768)` column to `notes` when pgvector backend

### Phase 3 — sqlite-vec (optional, low priority)

If we want a true single-file dev mode with no external vector DB:
- `sqlite-vec` SQLite extension (loads as `.so`)
- `VECTOR_BACKEND=sqlite-vec`
- Requires SQLite 3.41+ and loading the extension at connect time
- Useful for unit tests without Qdrant mock

---

## Key Design Constraints

- **No breaking change to existing SQLite users** — `DATABASE_URL=sqlite:///./data/memory.db` must keep working exactly as today
- **Same Docker image** for all modes — backend selected entirely by env vars
- **Alembic stays as the single migration system** — dialect-aware migrations, not separate migration trees
- **FTS5 stays for SQLite** — it's fast and already working; only PostgreSQL gets `tsvector`
- **pgvector requires PostgreSQL** — never try to use pgvector with SQLite (validate at startup)
- **Qdrant remains the default vector backend** — pgvector is opt-in

---

## Open Questions for Next Session

1. **PostgreSQL driver**: `psycopg2-binary` (sync, simpler) vs `asyncpg` (async, matches our async embedding calls)? Recommend `psycopg2-binary` first — the ORM layer is sync, async is only embedding calls which go through httpx anyway.

2. **`tsvector` language config**: use `'english'` or `'simple'`? `'simple'` is safer for multilingual notes (no stemming), `'english'` gives better recall for English-only deployments. Make it configurable (`FTS_LANGUAGE=simple`).

3. **Phase 2 timing**: implement pgvector in same branch or wait? Recommend separate branch — Phase 1 alone is already a testable, useful deliverable.
