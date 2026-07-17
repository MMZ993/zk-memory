# Data Model and Migrations

SQLAlchemy models in `src/app/models/database.py` and Alembic migrations in
`alembic/versions/` are the schema source of truth. Do not apply the examples
below directly to a running database; use Alembic instead.

```bash
uv run alembic upgrade head
```

The application supports SQLite for local use and PostgreSQL for deployments.
The selected `DB_BACKEND` determines the keyword-search implementation: SQLite
uses FTS5, while PostgreSQL uses a `tsvector` column, GIN index, and trigger.

## Tables

| Table | Purpose |
|---|---|
| `notes` | Permanent memory records and their embedding-sync state |
| `tags` | Globally unique tag names |
| `note_tags` | Note-to-tag associations |
| `relation_types` | Named link categories |
| `links` | Directed note-to-note relationships |
| `buffer_notes` | Short-lived, optionally processed memory entries |
| `metadata` | Application metadata |
| `admin_jobs` | Durable status for administrative embedding jobs |

All primary identifiers are UUID strings. `notes`, `tags`, `relation_types`,
`links`, and `buffer_notes` include timestamps appropriate to their lifecycle.

## Note embedding sync state

The SQL database is authoritative for notes. Qdrant holds the derived embedding
for a note. The `notes` table records reconciliation state so failed or
interrupted vector operations can be retried:

| Column | Meaning |
|---|---|
| `synced` | Whether Qdrant has the current embedding |
| `sync_status` | `pending`, `syncing`, `synced`, or `failed` |
| `sync_attempts` | Number of embedding attempts |
| `sync_last_error` | Most recent failure message |
| `sync_last_attempt_at` | Most recent attempt time |
| `sync_last_success_at` | Most recent successful sync time |

Use `POST /api/admin/sync-embeddings` to repair unsynced notes. A full re-embed
is available through the admin API when the embedding model or vector settings
change.

## Qdrant collection

The collection name defaults to `notes_embeddings`. Its vector size is
`EMBEDDING_DIMENSION` and must match the configured Ollama embedding model.
Qdrant points use the same UUID as their SQL note and store the derived vector
plus note metadata needed for retrieval.

## Schema changes

Create migrations through Alembic, review generated changes, then test them
against every supported backend:

```bash
uv run alembic revision --autogenerate -m "describe schema change"
uv run alembic upgrade head
make test
make test-integration-postgres
```

Dialect-specific indexes, full-text structures, and triggers may require manual
migration edits because Alembic cannot always infer them.
