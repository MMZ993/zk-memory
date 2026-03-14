# Next Session — Pick Up Here

## Previous Session Summary (2026-03-14)

### Scoped API keys

Replaced single `API_KEY` with 5 independent flat scoped keys.

**Design:** `MEMORY_API_KEY_READ/BUFFER/WRITE/DUMP/ADMIN` — flat, no implicit hierarchy except admin. Auth disabled when all vars empty. Each var accepts comma-separated keys. 401 = missing key, 403 = wrong scope (agent-readable errors).

**Changed files:**
- `src/app/core/config.py` — 5 `memory_api_key_*` fields replace `api_key`
- `src/app/api/deps.py` — `_check()` + `require_read/buffer/write/dump/admin` dependencies
- All 6 route files — each endpoint annotated with correct `require_*` dependency
- `.env.example` / `docker-compose.yml` — updated auth section
- `cli/README.md` — bash function pattern for multi-scope agents on same machine
- `docs/api-scopes.md` — full scope reference (endpoint map, agent config examples, key generation)

**All 77 unit tests still pass.**

### PostgreSQL migration — branch + plan created

Branch: `feat/postgres-migration`
Plan: `docs/plan-postgres-migration.md`

---

## Remaining Tasks (deferred, low priority)

- Test `memory dump --output /tmp/vault --format obsidian` against live seeded API
- `docs/api-specification.md` — Link model still shows embedded `relation_type` in some places; impl returns `relation_type_id` only

---

## Next Steps (prioritized)

### 1. PostgreSQL support — Phase 1 (branch ready: `feat/postgres-migration`)

See `docs/plan-postgres-migration.md` for full details. Work items:

1. **`session.py`** — dialect-aware engine: only apply `check_same_thread` and WAL/FK pragmas for SQLite
2. **`alembic/env.py`** — guard `_set_sqlite_pragmas` listener behind SQLite URL check
3. **`alembic/versions/d584390723bb`** — make FTS5 section dialect-aware (`op.get_bind().dialect.name`); add PostgreSQL path: `search_vector tsvector` column + GIN index + PG triggers
4. **`search_service.py`** — branch `search_keyword()` on dialect: SQLite → FTS5 MATCH, PostgreSQL → `tsvector @@ plainto_tsquery`
5. **`pyproject.toml`** — add `psycopg2-binary`
6. **`docker-compose.postgres.yml`** — PostgreSQL + Qdrant compose file
7. **`.env.example`** — add PostgreSQL `DATABASE_URL` example (commented out)
8. **Tests** — dialect-aware unit tests for keyword search

### 2. PostgreSQL + pgvector — Phase 2 (separate branch after Phase 1)

Eliminate Qdrant for single-node deployments. `VECTOR_BACKEND=qdrant|pgvector`.
See `docs/plan-postgres-migration.md` Phase 2 section.

### 3. GitLab CI (future)

Pipeline: unit tests on every push, integration tests on release with test LXC.

### 4. MCP server (future)

Wrap the memory API as an MCP server for Claude Desktop / other clients.

---

## Important Notes

### Active branch

```bash
git checkout feat/postgres-migration   # PostgreSQL work goes here
git checkout main                      # stable, all tests passing
```

### Current test status

- 77 unit tests + 48 integration tests (Docker stack)
- Run unit: `source .venv/bin/activate && pytest tests/test_services/ tests/test_api/ -v`
- Run integration: `make test-integration`

### Scoped API keys — auth behaviour

- All `MEMORY_API_KEY_*` unset → auth disabled (dev/local mode)
- Any var set → auth enforced on all non-public endpoints
- `MEMORY_API_KEY_ADMIN` passes every scope check
- 401 = no key sent, 403 = key present but wrong scope
- See `docs/api-scopes.md` for full endpoint → scope mapping

### Bash function pattern (CLI multi-scope)

```bash
memory_read()   { MEMORY_API_KEY=key_ro_xxx  memory "$@"; }
memory_buffer() { MEMORY_API_KEY=key_buf_xxx memory "$@"; }
memory_write()  { MEMORY_API_KEY=key_rw_xxx  memory "$@"; }
memory_admin()  { MEMORY_API_KEY=key_adm_xxx memory "$@"; }
```

### Alembic workflow

```bash
PYTHONPATH=src alembic current
PYTHONPATH=src alembic upgrade head
PYTHONPATH=src alembic revision --autogenerate -m "description"
PYTHONPATH=src alembic downgrade -1
PYTHONPATH=src alembic stamp head   # for existing DBs without alembic_version
```

### Seeding the DB for manual CLI testing

```bash
docker compose up -d
curl http://localhost:8000/api/health

source .venv/bin/activate
python - <<'EOF'
import httpx, sys
sys.path.insert(0, "tests")
from integration.fixtures import seed_data
seed_data(httpx.Client(base_url="http://localhost:8000"))
print("Seeded 14 notes and 13 links.")
EOF

cd cli && go build -o dist/memory . && cd ..
MEMORY_API_URL=http://localhost:8000 cli/dist/memory notes list --pretty
```

### PostgreSQL migration — open questions for next session

1. **Driver**: `psycopg2-binary` (sync, simpler) recommended over `asyncpg` — ORM layer is sync
2. **FTS language**: `'simple'` (multilingual safe, no stemming) vs `'english'` — make it `FTS_LANGUAGE` env var defaulting to `simple`
3. **Phase 2 timing**: implement pgvector in same branch or separate? Recommend separate.

### Deployment mode ladder (planned)

| Mode | Stack | Compose file |
|---|---|---|
| Dev / home lab | SQLite + Qdrant | `docker-compose.yml` (current) |
| Single-node prod | PostgreSQL + pgvector | `docker-compose.simple.yml` (Phase 2) |
| Distributed / k8s | PostgreSQL + Qdrant | `docker-compose.postgres.yml` (Phase 1) |

---

## Previous NEXT_SESSION.md Review

- ✅ Scoped API keys — fully implemented and committed
- ✅ Alembic setup — completed previous session, committed this session
- ⬜ Test `memory dump` against live API — still deferred (low priority)
- ⬜ Fix `LinkResponse` embed in api-specification.md — still deferred (low priority)
- ⬜ GitLab CI / MCP server — still future
- ✅ PostgreSQL migration — branch created, plan written, ready to implement
