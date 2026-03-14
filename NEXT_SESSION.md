# Next Session — Pick Up Here

## Previous Session Summary (2026-03-14)

### PostgreSQL Phase 1 — complete

Implemented full dialect-aware SQLite + PostgreSQL support on branch `feat/postgres-migration`.

**Key decisions made this session:**
- `DB_BACKEND=sqlite|postgres` env var added — explicit, not inferred from URL
- Driver: `psycopg[binary]` (psycopg3) — URL must use `postgresql+psycopg://` scheme
- FTS language: `'english'` hardcoded (stemming enabled; no env var needed)
- Dialect detection in migrations: `op.get_bind().dialect.name` — no deprecated APIs

**Changed files:**
- `src/app/core/config.py` — `db_backend: str = "sqlite"` field
- `src/app/db/session.py` — SQLite-only `check_same_thread` + WAL/FK pragmas
- `alembic/env.py` — pragma listener guarded behind SQLite check
- `alembic/versions/d584390723bb` — FTS5 path (SQLite) vs tsvector+GIN+trigger path (PostgreSQL)
- `src/app/services/search_service.py` — keyword search branches on `db_backend`
- `requirements.txt` + `pyproject.toml` — `psycopg[binary]>=3.1.0`
- `.env.example` + `docker-compose.yml` — `DB_BACKEND` added
- `docker-compose.postgres.yml` — production PostgreSQL + Qdrant compose
- `docker-compose.test.postgres.yml` — isolated test stack (API: 8002, PG: 5433, Qdrant: 6335)
- `Makefile` — `test-integration-postgres` / `test-integration-postgres-down`
- `scripts/dev-reset-postgres.sh` — wipe + recreate schema for dev/test postgres stacks

**Test status: 77 unit + 48 integration (SQLite) + 48 integration (PostgreSQL) = 173 tests, all passing.**

---

## Remaining Tasks (deferred, low priority)

- Test `memory dump --output /tmp/vault --format obsidian` against live seeded API
- `docs/api-specification.md` — Link model still shows embedded `relation_type` in some places; impl returns `relation_type_id` only

---

## Next Steps (prioritized)

### 1. Merge `feat/postgres-migration` → `main`

Phase 1 is complete and all tests pass. Ready to merge.

### 2. GitLab CI (future)

Pipeline: unit tests on every push, integration tests on release with test LXC.

### 3. MCP server (future)

Wrap the memory API as an MCP server for Claude Desktop / other clients.

### Out of scope (decided 2026-03-14)

- **pgvector** — Qdrant stays as the only vector backend. `synced` column handles consistency. pgvector may be revisited alongside MCP if there's a compelling reason.
- **sqlite-vec** — same reasoning; not worth the complexity for dev mode.

---

## Important Notes

### Active branches

```bash
git checkout feat/postgres-migration   # Phase 1 complete, ready to merge
git checkout main                      # stable, SQLite only
```

### Current test status

- 77 unit tests + 48 SQLite integration + 48 PostgreSQL integration = 173 total
- Unit: `source .venv/bin/activate && pytest tests/test_services/ tests/test_api/ -v`
- Integration (SQLite): `make test-integration`
- Integration (PostgreSQL): `make test-integration-postgres`

### DB_BACKEND env var

```
DB_BACKEND=sqlite    # default — SQLite + FTS5
DB_BACKEND=postgres  # PostgreSQL + tsvector
```

Must match the `DATABASE_URL` scheme. When `postgres`, URL must be `postgresql+psycopg://...` (psycopg3 driver — `postgresql://` would try to load psycopg2 which is not installed).

### Dev reset scripts

```bash
./scripts/dev-reset-postgres.sh        # wipe prod postgres stack
./scripts/dev-reset-postgres.sh test   # wipe test postgres stack (port 8002)
```

Drops schema, re-runs Alembic, deletes Qdrant collection.

### Deployment mode ladder

| Mode | Stack | Compose file |
|---|---|---|
| Dev / home lab | SQLite + Qdrant | `docker-compose.yml` |
| Distributed / k8s | PostgreSQL + Qdrant | `docker-compose.postgres.yml` |
| Single-node prod | PostgreSQL + pgvector | `docker-compose.simple.yml` (Phase 2) |

### Alembic workflow

```bash
PYTHONPATH=src alembic current
PYTHONPATH=src alembic upgrade head
PYTHONPATH=src alembic revision --autogenerate -m "description"
PYTHONPATH=src alembic downgrade -1
PYTHONPATH=src alembic stamp head   # for existing DBs without alembic_version
```

Note: FTS5 virtual table, tsvector column, GIN index, and triggers are **not** visible to autogenerate — they are managed manually in the migration file.

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

### Scoped API keys — auth behaviour

- All `MEMORY_API_KEY_*` unset → auth disabled (dev/local mode)
- Any var set → auth enforced on all non-public endpoints
- `MEMORY_API_KEY_ADMIN` passes every scope check
- 401 = no key sent, 403 = key present but wrong scope
- See `docs/api-scopes.md` for full endpoint → scope mapping

---

## Previous NEXT_SESSION.md Review

- ✅ PostgreSQL Phase 1 — fully implemented, tested, 48/48 integration tests passing
- ⬜ Test `memory dump` against live API — still deferred (low priority)
- ⬜ Fix `LinkResponse` embed in api-specification.md — still deferred (low priority)
- ⬜ GitLab CI / MCP server — still future
