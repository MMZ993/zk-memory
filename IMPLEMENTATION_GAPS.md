# Implementation Gaps

Short backlog of items not yet covered in the main implementation guide. Work through these after the core phases are done.

## Missing Endpoints

**Resolved** — implementation spec written in `docs/implementation-guide.md` Phase 10.

All endpoints below now have service + route code in Phase 10:

- `GET /api/notes` — list notes (Phase 10.1 / 10.10)
- `GET /api/buffer/{id}` — get single buffer note (Phase 10.2 / 10.11)
- `DELETE /api/buffer/{id}` — delete buffer note (Phase 10.2 / 10.11)
- `GET /api/notes/{id}/links` — get note's links with direction filter (Phase 10.5 / 10.10)
- `GET /api/notes/{id}/tags` — get note's tags (Phase 10.3 / 10.10)
- `POST /api/notes/{id}/tags` — add tag to note (Phase 10.3 / 10.10)
- `DELETE /api/notes/{id}/tags/{tag_id}` — remove tag from note (Phase 10.3 / 10.10)
- `GET /api/tags` — list tags with usage counts (Phase 10.3 / 10.12)
- `POST /api/tags` — create standalone tag (Phase 10.3 / 10.12)
- `GET /api/relations` — list relation types with link counts (Phase 10.4 / 10.13)
- `POST /api/relations` — create relation type (Phase 10.4 / 10.13)
- `GET /api/relations/{id}` — get relation type (Phase 10.4 / 10.13)
- `PATCH /api/relations/{id}` — update relation type (Phase 10.4 / 10.13)
- `DELETE /api/relations/{id}` — delete relation type restricted if links exist (Phase 10.4 / 10.13)
- `GET /api/export` — export all notes to markdown zip (Phase 10.6 / 10.14)
- `GET /api/export/notes` — export notes only (Phase 10.6 / 10.14)
- `GET /api/export/buffer` — export buffer notes (Phase 10.6 / 10.14)
- `POST /api/import` — import from markdown directory (Phase 10.6 / 10.14)
- `GET /api/stats` — system statistics (Phase 10.8 / 10.15)
- `GET /api/config` — current configuration values (Phase 10.8 / 10.15)
- `DELETE /api/buffer/processed` — cleanup old processed buffer notes (Phase 10.2 / 10.11)
- `GET /api/admin/backups` — list backups (Phase 10.8 / 10.15)
- `POST /api/admin/restore/{id}` — restore from backup (Phase 10.8 / 10.15)
- `POST /api/admin/reembed` — purge and regenerate all embeddings (Phase 10.8 / 10.15)
- `GET /api/admin/reembed/status` — re-embed job progress (Phase 10.8 / 10.15)
- `POST /api/admin/sync-embeddings` — trigger sync for unsynced notes (Phase 10.8 / 10.15)

## Services with No Implementation Spec

**Resolved** — spec written in Phase 10:

- `app/services/export_service.py` — Phase 10.6
- `app/utils/markdown.py` — Phase 10.7

## Database

- ~~**SQLite WAL mode**~~ ✅ Fixed — `PRAGMA journal_mode=WAL` added to `app/db/session.py` via `@event.listens_for(engine, "connect")`
- ~~**Qdrant payload drift**~~ ✅ Fixed — `_build_qdrant_payload()` helper in `app/services/note_service.py` used by both `_embed_and_sync` and `sync_unsynced_notes`; both now include `content_length` and `summary`

## Search

- ~~**Graph depth limit**~~ ✅ Fixed — `MAX_GRAPH_DEPTH = 3` hard cap enforced in `search_graph()` (Phase 10.9); configurable down via `graph_depth` param (1–3), never up

## Other

- No rate limiting or request body size limits defined — relevant if exposing over network
