# API Reference

A concise reference for the running API. FastAPI serves the complete request and
response schema at [`/docs`](/docs) and [`/openapi.json`](/openapi.json).

## Authentication

Authentication is disabled when every `MEMORY_API_KEY_*` variable is unset. When
enabled, send a scoped key in the `X-API-Key` header. An admin key satisfies every
scope. See [API access scopes](api-scopes.md) for key configuration.

| Scope | Operations |
|---|---|
| Public | `GET /`, `GET /api/health`, `GET /api/readiness`, `GET /metrics` |
| `read` | Read notes, buffer notes, tags, relations, search, graph, links, and stats |
| `buffer` | Create buffer notes |
| `write` | Create, update, delete, tag, link, process, or clean up memory |
| `dump` | Export notes and buffer notes |
| `admin` | Read configuration and run embedding administration |

`/metrics` is intentionally unauthenticated. Restrict it to trusted monitoring
networks.

## Endpoints

| Scope | Method | Path |
|---|---|---|
| Public | GET | `/` |
| Public | GET | `/api/health` |
| Public | GET | `/api/readiness` |
| Public | GET | `/metrics` |
| read | GET | `/api/notes/` |
| read | GET | `/api/notes/search` |
| read | GET | `/api/notes/{note_id}` |
| read | GET | `/api/notes/{note_id}/graph` |
| read | GET | `/api/notes/{note_id}/links` |
| read | GET | `/api/notes/{note_id}/tags` |
| write | POST | `/api/notes/` |
| write | PATCH | `/api/notes/{note_id}` |
| write | DELETE | `/api/notes/{note_id}` |
| write | POST | `/api/notes/links` |
| write | DELETE | `/api/notes/links/{link_id}` |
| write | POST | `/api/notes/{note_id}/tags` |
| write | DELETE | `/api/notes/{note_id}/tags/{tag_id}` |
| buffer | POST | `/api/buffer/` |
| read | GET | `/api/buffer/` |
| read | GET | `/api/buffer/{note_id}` |
| write | POST | `/api/buffer/{note_id}/process` |
| write | DELETE | `/api/buffer/{note_id}` |
| write | DELETE | `/api/buffer/cleanup` |
| read | GET | `/api/tags/` |
| write | POST | `/api/tags/` |
| read | GET | `/api/relations/` |
| read | GET | `/api/relations/{relation_id}` |
| write | POST | `/api/relations/` |
| write | PUT | `/api/relations/{relation_id}` |
| write | DELETE | `/api/relations/{relation_id}` |
| dump | GET | `/api/export/` |
| dump | GET | `/api/export/notes` |
| dump | GET | `/api/export/buffer` |
| read | GET | `/api/stats` |
| admin | GET | `/api/config` |
| admin | POST | `/api/admin/reembed` |
| admin | GET | `/api/admin/reembed/status` |
| admin | POST | `/api/admin/sync-embeddings` |

## Common requests

```bash
# Read notes
curl -H "X-API-Key: $MEMORY_API_KEY" \
  "http://localhost:8000/api/notes/?limit=20"

# Create a note
curl -X POST -H "Content-Type: application/json" \
  -H "X-API-Key: $MEMORY_API_KEY" \
  -d '{"title":"Example","content":"Memory content"}' \
  http://localhost:8000/api/notes/

# Search notes
curl -H "X-API-Key: $MEMORY_API_KEY" \
  "http://localhost:8000/api/notes/search?q=example&search_type=hybrid"
```
