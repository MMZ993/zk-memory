# AI Agent Memory System

Local-first memory backend for agents, with a Go CLI as the main frontend.

## Goals

- Keep the stack simple and reliable.
- Prefer local defaults (SQLite + Qdrant + Ollama).
- Expose a clean HTTP API and a stable CLI.

## Current Feature Set

- Buffer notes (fast capture, no embedding on write)
- Permanent notes (CRUD)
- Tags, relations, note links
- Search modes: semantic, keyword, hybrid, graph traversal
- Admin operations: stats, config, unsynced repair, re-embed
- Readiness endpoint for DB + Qdrant dependency checks

## Architecture

- API: FastAPI (`src/main.py`, routers in `src/app/api`)
- SQL store: SQLite (default) or PostgreSQL (optional)
- Vector store: Qdrant
- Embeddings: local Ollama (`nomic-embed-text` default)
- CLI: Go + Cobra (`cli/`)

## Quick Start (Local)

1) Install dependencies:

```bash
uv sync
```

2) Start Qdrant (if not already running):

```bash
docker run -p 6333:6333 qdrant/qdrant
```

3) Ensure Ollama is running and model is available:

```bash
ollama pull nomic-embed-text
```

4) Start API:

```bash
uv run uvicorn main:app --reload
```

API default: `http://localhost:8000`

## Docker Compose

```bash
docker compose up -d --build
```

Primary compose files:

- `docker-compose.yml` (SQLite)
- `docker-compose.postgres.yml` (PostgreSQL)
- `docker-compose.deploy.yml` (image-based UAT/PROD deployment)

## CLI

Build:

```bash
cd cli && go build -o dist/memory .
```

Configure:

```bash
export MEMORY_API_URL=http://localhost:8000
export MEMORY_API_KEY=...
```

Examples:

```bash
memory notes list
memory notes search "query" --mode hybrid
memory admin health --pretty
memory admin stats --pretty
```

`memory admin health` reports:

- API health status/version (`/api/health`)
- Dependency readiness (`/api/readiness`)

## Scripts

Current scripts in `scripts/`:

- `scripts/seed.py`
- `scripts/reset_integration.sh`
- `scripts/dev-reset-postgres.sh`

## Testing

```bash
make test
make test-cli
make test-integration
make test-integration-auth
make test-integration-postgres
```

## CI/CD

- Pipeline definition: `.gitlab-ci.yml`
- CI/CD contract and artifact outputs: `docs/ci-cd.md`
- Deploy runtime contract: `docs/deploy-runtime.md`
- UAT/PROD rollout runbook: `docs/uat-prod-rollout.md`

## Configuration

Use `.env.example` as baseline. Important keys:

- `DATABASE_URL`, `DB_BACKEND`
- `QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_COLLECTION`
- `OLLAMA_HOST`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`
- `MEMORY_API_KEY_READ|BUFFER|WRITE|DUMP|ADMIN`
- `CORS_ALLOW_*`

CORS notes:

- `CORS_ALLOW_ORIGINS` accepts a comma-separated or JSON list.
- `CORS_ALLOW_ORIGIN_REGEX` is the local-safe fallback; set empty to disable fallback.

See `docs/configuration.md` for full details.

## Known Limitations

This is a local-first personal application. Some design decisions prioritize simplicity over scale:

### Single-Worker Architecture

Admin job state (re-embed, sync-embeddings) uses in-memory progress tracking. This is lost on server restart, but durable job state is persisted in the `admin_jobs` table. **Not suitable for multi-instance deployments** without external coordination.

### Export Endpoints

`/api/export/notes` and `/api/export/buffer` load all records into memory without pagination. Acceptable for personal datasets (thousands of notes); may require modification for larger deployments.

### Background Task Reliability

Async embedding mode (`EMBEDDING_MODE=async`) uses FastAPI `BackgroundTasks`, which are tied to the request process. Server restarts interrupt in-flight embeddings. Failed embeddings are tracked in the database and can be recovered via `/api/admin/sync-embeddings`. Default mode is `sync` (safer).

### No Rate Limiting

No rate limiting on API endpoints. Acceptable for personal/local use where you control all clients.

### SQLite FTS5 Query Handling

Keyword search passes user input to FTS5 with minimal escaping (double quotes only). Special FTS5 operators are not sanitized. Acceptable for personal use.
