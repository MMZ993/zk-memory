# Configuration

Copy `.env.example` to `.env` for local development. The application loads this
file at startup; environment variables supplied by Docker Compose or the process
environment take precedence.

```bash
cp .env.example .env
```

## Application and HTTP

| Variable | Default | Purpose |
|---|---:|---|
| `APP_NAME` | `AI Agent Memory System` | Application name |
| `DEBUG` | `false` | Enable debug mode |
| `API_HOST` | `0.0.0.0` | Bind address |
| `API_PORT` | `8000` | Bind port |
| `LOG_LEVEL` | `INFO` | Python log level |
| `LOG_FORMAT` | `json` | `json` or text log format |

CORS is local-safe by default. `CORS_ALLOW_ORIGINS`, `CORS_ALLOW_METHODS`, and
`CORS_ALLOW_HEADERS` accept a comma-separated or JSON list.
`CORS_ALLOW_ORIGIN_REGEX` defaults to localhost and 127.0.0.1 on any port. Set empty to disable fallback.

## Data stores

| Variable | Default | Purpose |
|---|---:|---|
| `DB_BACKEND` | `sqlite` | `sqlite` for local use or `postgres` for PostgreSQL |
| `DATABASE_URL` | `sqlite:///./data/memory.db` | SQLAlchemy connection URL |
| `QDRANT_HOST` | `localhost` | Qdrant host |
| `QDRANT_PORT` | `6333` | Qdrant port |
| `QDRANT_COLLECTION` | `notes_embeddings` | Qdrant collection name |
| `QDRANT_API_KEY` | empty | Optional Qdrant API key |

`DB_BACKEND` must match the URL dialect. For PostgreSQL, use the psycopg URL
scheme:

```env
DB_BACKEND=postgres
DATABASE_URL=postgresql+psycopg://memory:memory@postgres:5432/memory
```

Use `docker-compose.postgres.yml` for a local PostgreSQL stack and
`docker-compose.deploy.yml` for image-based UAT/production deployment.

## Embeddings and notes

| Variable | Default | Purpose |
|---|---:|---|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama endpoint |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Local Ollama embedding model |
| `EMBEDDING_DIMENSION` | `768` | Vector dimension; must match the model and collection |
| `EMBEDDING_MODE` | `sync` | `sync` or `async` embedding on note writes |
| `EMBEDDING_TASK_PREFIX` | `false` | Add supported model task prefixes when indexing/searching |
| `NOTE_MAX_CONTENT_LENGTH` | `2048` | Maximum note content length; `0` disables the limit |
| `BUFFER_RETENTION_DAYS` | `7` | Retain processed buffer notes for this many days |
| `MARKDOWN_DIR` | `./data/notes` | Destination used by file-export workflows |

Changing `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`, or
`EMBEDDING_TASK_PREFIX` after data is indexed requires a full re-embed.

## Authentication

Authentication is disabled when all key variables are empty. When enabled, API
clients send one configured key in the `X-API-Key` header. Keys may be
comma-separated to support rotation.

| Variable | Scope |
|---|---|
| `MEMORY_API_KEY_READ` | Read notes, buffer notes, tags, relations, search, and stats |
| `MEMORY_API_KEY_BUFFER` | Create buffer notes |
| `MEMORY_API_KEY_WRITE` | Modify notes, tags, relations, links, and buffer notes |
| `MEMORY_API_KEY_DUMP` | Use export endpoints |
| `MEMORY_API_KEY_ADMIN` | All scopes plus administrative operations |

Scopes are independent; the admin key satisfies every scope. See
[API access scopes](api-scopes.md) for the endpoint mapping.

## Example local configuration

```env
DB_BACKEND=sqlite
DATABASE_URL=sqlite:///./data/memory.db
QDRANT_HOST=localhost
OLLAMA_HOST=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIMENSION=768
```
