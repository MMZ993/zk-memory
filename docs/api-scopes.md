# API Access Scopes

## Overview

The Memory API uses **scoped API keys** to enforce the principle of least privilege. Each agent or skill receives only the key(s) needed for its specific role — reducing context noise, limiting blast radius if a key is compromised, and making agent roles explicit.

Auth is **opt-in**: if no `MEMORY_API_KEY_*` variable is set, all requests are accepted without authentication (development / local use).

---

## Scopes

| Scope | Env var | Purpose |
|-------|---------|---------|
| `read` | `MEMORY_API_KEY_READ` | Read-only access to all memory (notes, search, tags, links, buffer) |
| `buffer` | `MEMORY_API_KEY_BUFFER` | Append to buffer only — no reads, no changes |
| `write` | `MEMORY_API_KEY_WRITE` | Modify memory: create/edit/delete notes, tags, links; process buffer |
| `dump` | `MEMORY_API_KEY_DUMP` | Export endpoints only |
| `admin` | `MEMORY_API_KEY_ADMIN` | Full access — all endpoints, no restrictions |

Scopes are **flat and independent**. There is no implicit hierarchy except for `admin`, which passes every scope check. If an agent needs multiple scopes (e.g., the write agent needs `read` + `write`), provide both keys in its environment.

---

## Endpoint → Scope Mapping

### Public (no key required)
| Method | Path |
|--------|------|
| GET | `/` |
| GET | `/api/health` |
| GET | `/api/readiness` |
| GET | `/metrics` |

### READ
| Method | Path |
|--------|------|
| GET | `/api/notes/` |
| GET | `/api/notes/search` |
| GET | `/api/notes/{note_id}` |
| GET | `/api/notes/{note_id}/graph` |
| GET | `/api/notes/{note_id}/links` |
| GET | `/api/notes/{note_id}/tags` |
| GET | `/api/buffer/` |
| GET | `/api/buffer/{note_id}` |
| GET | `/api/tags/` |
| GET | `/api/relations/` |
| GET | `/api/relations/{relation_id}` |
| GET | `/api/stats` |

### BUFFER
| Method | Path |
|--------|------|
| POST | `/api/buffer/` |

### WRITE
| Method | Path |
|--------|------|
| POST | `/api/notes/` |
| PATCH | `/api/notes/{note_id}` |
| DELETE | `/api/notes/{note_id}` |
| POST | `/api/notes/links` |
| DELETE | `/api/notes/links/{link_id}` |
| POST | `/api/notes/{note_id}/tags` |
| DELETE | `/api/notes/{note_id}/tags/{tag_id}` |
| POST | `/api/tags/` |
| POST | `/api/relations/` |
| PUT | `/api/relations/{relation_id}` |
| DELETE | `/api/relations/{relation_id}` |
| POST | `/api/buffer/{note_id}/process` |
| DELETE | `/api/buffer/{note_id}` |
| DELETE | `/api/buffer/cleanup` |

### DUMP
| Method | Path |
|--------|------|
| GET | `/api/export/` |
| GET | `/api/export/notes` |
| GET | `/api/export/buffer` |

### ADMIN
| Method | Path |
|--------|------|
| GET | `/api/config` |
| POST | `/api/admin/reembed` |
| GET | `/api/admin/reembed/status` |
| POST | `/api/admin/sync-embeddings` |

---

## Configuration

Each env var accepts a single key or a **comma-separated list** of keys (useful when rotating keys or sharing a scope across multiple agents).

```env
MEMORY_API_KEY_READ=key_ro_abc123
MEMORY_API_KEY_BUFFER=key_buf_xyz789
MEMORY_API_KEY_WRITE=key_rw_def456
MEMORY_API_KEY_DUMP=key_dump_ghi012
MEMORY_API_KEY_ADMIN=key_adm_jkl345

# Multiple keys for the same scope (comma-separated):
MEMORY_API_KEY_READ=key_ro_abc123,key_ro_old456
```

---

## Typical Agent Configurations

### Read-only agent (e.g., Claude Code skill — memory lookup)
```env
MEMORY_API_KEY=key_ro_abc123   # send as X-Api-Key header
```
Scope: `read`

### Buffer-save agent (e.g., end-of-session memory dump)
```env
MEMORY_API_KEY=key_buf_xyz789
```
Scope: `buffer`

### Read + buffer agent (bundled skill — search + save to buffer)
Provide two keys, one per operation, or give the agent both headers:
```env
MEMORY_API_KEY_READ=key_ro_abc123
MEMORY_API_KEY_BUFFER=key_buf_xyz789
```
Agent uses the `read` key for GET requests and the `buffer` key for POST /buffer.

### Memory write agent (overnight consolidation — reads notes, processes buffer, writes notes)
```env
MEMORY_API_KEY_READ=key_ro_abc123
MEMORY_API_KEY_WRITE=key_rw_def456
```

### Dump agent (periodic export)
```env
MEMORY_API_KEY=key_dump_ghi012
```
Scope: `dump`

### Human / admin
```env
MEMORY_API_KEY=key_adm_jkl345
```
Scope: `admin` — passes all checks.

---

## Auth Behavior

- **Disabled**: all `MEMORY_API_KEY_*` vars unset → every request is accepted (dev/local mode)
- **Enabled**: any key var is set → `X-Api-Key` header is required on all non-public endpoints
- **Admin bypass**: a key present in `MEMORY_API_KEY_ADMIN` passes every scope check
- **Missing key**: HTTP 401
- **Wrong key or insufficient scope**: HTTP 403

---

## Key Naming Convention

Keys have no enforced format, but a readable prefix helps when managing multiple keys:

```
key_ro_<random>     # read
key_buf_<random>    # buffer
key_rw_<random>     # write
key_dump_<random>   # dump
key_adm_<random>    # admin
```

Generate a key:
```bash
python3 -c "import secrets; print('key_ro_' + secrets.token_urlsafe(24))"
```
