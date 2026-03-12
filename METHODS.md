# API Operations Reference

## Authentication
All endpoints accept optional `X-API-Key` header when `API_KEY` env var is set.

---

## Buffer Notes
Short-term memory — fast SQLite writes, no embeddings.

| Method | Endpoint | Parameters | Returns / Behavior |
|--------|----------|------------|--------------------|
| `POST` | `/api/buffer` | body: `content` (req), `meta` (opt: source, tags, custom fields) | Creates buffer note. SQLite-only write, no embedding. Returns BufferNote. |
| `GET` | `/api/buffer` | query: `processed` (bool), `limit` (default 100), `offset` | Lists buffer notes. Filter by processed status. Returns array of BufferNote. |
| `GET` | `/api/buffer/{id}` | path: `id` (uuid) | Returns single BufferNote or 404. |
| `POST` | `/api/buffer/{id}/process` | path: `id` (uuid) | Marks note processed: sets `processed=true`, `processed_at=now`. Returns updated BufferNote. |
| `DELETE` | `/api/buffer/{id}` | path: `id` (uuid) | Deletes buffer note. Returns success message. |
| `DELETE` | `/api/buffer/cleanup` | — | Deletes processed buffer notes older than `BUFFER_RETENTION_DAYS`. If retention=0, disabled — returns `{"deleted": 0, "disabled": true}`. Returns `{"deleted": N}`. |

---

## Notes
Long-term memory — full CRUD with vector embeddings.

| Method | Endpoint | Parameters | Returns / Behavior |
|--------|----------|------------|--------------------|
| `POST` | `/api/notes` | body: `title` (req), `content` (req), `summary` (opt), `tags` (opt) | Creates note, triggers async embedding → Qdrant upsert, `synced=true`. Returns Note. |
| `GET` | `/api/notes` | query: `tags` (comma-sep), `limit` (default 20), `offset`, `sort` (created_at/updated_at), `order` (asc/desc) | Lists notes with optional tag filter. Returns array of Note. |
| `GET` | `/api/notes/{id}` | path: `id` (uuid) | Returns Note with tags and links, or 404. |
| `PATCH` | `/api/notes/{id}` | path: `id`, body: `title`/`content`/`summary`/`tags` (all opt) | Partial update. If content changed, regenerates embedding and re-syncs to Qdrant. Returns updated Note. |
| `DELETE` | `/api/notes/{id}` | path: `id` (uuid) | Deletes note from SQLite and removes vector from Qdrant. Returns success message. |
| `GET` | `/api/notes/search` | query: `q` (text, req), `tags` (comma-sep), `limit` (default 10), `threshold` (0–1, default 0.7), `search_type` (semantic/keyword/hybrid) | Searches notes by text. Returns full note objects including tags, links, and uuid, with similarity score. Returns `{"results": [...], "total": N}`. |
| `GET` | `/api/notes/{id}/graph` | path: `id` (uuid), query: `depth` (int 1–3, default 1) | Traverses the note link graph outward from the given note up to `depth` levels. Returns connected notes with tags, links, uuid, and distance from the starting note. |
| `GET` | `/api/notes/{id}/links` | path: `id`, query: `direction` (incoming/outgoing/all, default all), `limit` (default 50) | Returns all links attached to a note, with relation type details. |
| `GET` | `/api/notes/{id}/tags` | path: `id` (uuid) | Returns array of Tag objects for the note. |
| `POST` | `/api/notes/{id}/tags` | path: `id`, body: `name` (req) | Adds tag to note. Creates tag if it doesn't exist. Returns Tag object. |
| `DELETE` | `/api/notes/{id}/tags/{tag_id}` | path: `id`, `tag_id` | Removes tag association from note (tag record stays). Returns success message. |

### Search Types (`search_type` param)
- `semantic` — vector similarity via Qdrant
- `keyword` — SQLite FTS5 full-text on title + content
- `hybrid` — combines semantic + keyword scores (default)

---

## Links
Directed relationships between notes.

| Method | Endpoint | Parameters | Returns / Behavior |
|--------|----------|------------|--------------------|
| `POST` | `/api/notes/links` | body: `source_id` (req), `target_id` (req), `relation_type` (req, string name), `description` (opt) | Creates link. Auto-creates the relation type if it doesn't exist. Returns Link object. |
| `DELETE` | `/api/notes/links/{id}` | path: `id` (uuid) | Deletes link. Returns success message. |

---

## Tags
Global tag registry with per-note association.

| Method | Endpoint | Parameters | Returns / Behavior |
|--------|----------|------------|--------------------|
| `GET` | `/api/tags` | query: `limit` (default 100), `offset` | Lists all tags with usage counts. Returns array of Tag. |
| `POST` | `/api/tags` | body: `name` (req) | Creates standalone tag. Returns Tag. 409 if name already exists. |

---

## Relation Types
Named, typed link categories (e.g. "related-to", "contradicts").

| Method | Endpoint | Parameters | Returns / Behavior |
|--------|----------|------------|--------------------|
| `GET` | `/api/relations` | — | Lists all relation types with link usage counts. Returns array of RelationType. |
| `POST` | `/api/relations` | body: `name` (req, unique), `description` (opt), `is_bidirectional` (bool, default false) | Creates relation type. Returns RelationType. |
| `GET` | `/api/relations/{id}` | path: `id` (uuid) | Returns single RelationType or 404. |
| `PUT` | `/api/relations/{id}` | path: `id`, body: `name`/`description`/`is_bidirectional` (all opt) | Full-ish update of relation type. Returns updated RelationType. |
| `DELETE` | `/api/relations/{id}` | path: `id` (uuid) | Deletes relation type. Fails (409 or 422) if any links reference it. |

---

## Export
Read-only JSON dumps for agent or human consumption.

| Method | Endpoint | Parameters | Returns / Behavior |
|--------|----------|------------|--------------------|
| `GET` | `/api/export` | — | Full dump: all notes with tags. Returns JSON array. |
| `GET` | `/api/export/notes` | — | Notes only. Returns JSON array. |
| `GET` | `/api/export/buffer` | — | Buffer notes only. Returns JSON array. |

No import endpoint — bulk ingestion is done via repeated `POST /api/notes`.

---

## Admin / System

| Method | Endpoint | Parameters | Returns / Behavior |
|--------|----------|------------|--------------------|
| `GET` | `/api/health` | — | Returns status of SQLite and Qdrant connections + version. |
| `GET` | `/api/stats` | — | Counts for notes (total/synced/unsynced/today), links, tags, buffer, and Qdrant vector store. |
| `GET` | `/api/config` | — | Safe config subset: embedding provider/model/dimension, buffer retention, version. Never exposes secrets. |
| `POST` | `/api/admin/reembed` | body: `confirm` (must equal exact confirmation string) | Purges all Qdrant vectors and regenerates embeddings for all notes. Runs as background job. Returns `{"status": "started", "total_notes": N}`. |
| `GET` | `/api/admin/reembed/status` | — | Returns current reembed job status: `idle`, `in_progress`, or `finished`. Stored in `metadata` table. |
| `POST` | `/api/admin/sync-embeddings` | — | Triggers background embedding for all notes where `synced=false`. Returns `{"status": "started", "pending_notes": N}`. |

---

**Total: 31 endpoints** across 7 resource groups.
