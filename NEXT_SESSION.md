# Next Session — Pick Up Here

## Previous Session Summary

Full project review + two production bug fixes + CLI planning:

### Bug fixes (committed: `6144230`)

- **`src/app/db/session.py`** — `init_db()` now creates the `notes_fts` FTS5 virtual table
  and 3 triggers (insert/update/delete). Previously FTS5 only existed in integration test
  setup, so keyword search silently returned `[]` in production.
- **`src/app/services/search_service.py`** — `search_hybrid()` now keeps the highest score
  per note across semantic + keyword results. Previously it kept the first (semantic) score,
  which caused keyword matches (score=1.0) to be dropped by the threshold filter when the
  same note also appeared in semantic results with a low score.

### CLI planning

- Designed Go CLI tool — see **`docs/cli-plan.md`** for full spec
- Language: Go (single static binary, deployed on agent VM separate from API VM)
- Config: ENV vars only (`MEMORY_API_URL`, `MEMORY_API_KEY`, `MEMORY_TIMEOUT`)
- Output: JSON default + `--pretty` flag for humans
- Commands: 1:1 mapping with all API endpoints
- Location: `cli/` folder in this repo
- `internal/client` package shared with future MCP server

---

## Remaining Tasks

### Bash scripts (likely dropped)
`scripts/export_notes.sh` and `scripts/sync_back.sh` were deferred in Phase 9.
With the CLI implemented, these become one-liners (`memory export notes`). Probably not needed.

### GitLab CI pipeline (future, homelab not active yet)
- **Every push**: unit tests only
- **Merge to main / release tag**: spin up test LXC, run integration tests, gate prod deploy
- All env-var driven

---

## Next Steps (prioritized)

1. **(Start now)** Implement the Go CLI — see `docs/cli-plan.md` for full spec
   - Suggested order:
     1. `cli/` skeleton: `go.mod`, `main.go`, cobra root, `internal/client/client.go`
     2. `notes search` + `notes create` (validates full stack end-to-end)
     3. Rest of `notes` CRUD
     4. `buffer` commands
     5. `tags`, `relations`, `export`, `admin`
     6. `--pretty` output for all commands
     7. Makefile with cross-compile targets
2. **(Optional)** Update `docs/testing-plan.md` — currently has aspirational example code, not harmful but out of date
3. **(Future)** GitLab CI pipeline when homelab is back up
4. **(Future)** MCP server — `internal/client` package reused, thin MCP wrapper

---

## Important Notes

### API status
- All 125 tests passing (77 unit + 48 integration)
- Run unit: `source .venv/bin/activate && pytest tests/test_services/ tests/test_api/ -v`
- Run integration: `docker compose up qdrant -d && INTEGRATION_TESTS=1 pytest tests/integration/ -v`

### Critical design constraints (do not break)
- **Two-phase sync**: notes written with `synced=False` → embedded → `synced=True`. Retry via `POST /api/admin/sync-embeddings`.
- **Route ordering**: `/api/notes/search` and `/api/notes/links` MUST stay before `/{note_id}`. `/api/buffer/cleanup` MUST stay before `/api/buffer/{note_id}`.
- **`Note.tags` property** on ORM model — do not remove. Makes `NoteResponse.model_validate(note)` work.
- **`StaticPool`** in `tests/test_api/conftest.py` — required for SQLite in-memory with TestClient threads.
- **Export is JSON arrays**, not ZIP/markdown.
- **`client.query_points()` not `client.search()`** — qdrant-client removed `.search()`. The mock in `tests/conftest.py` uses `mock_client.query_points.return_value.points = []`.
- **Search param is `search_type`** (not `mode`) — `?search_type=keyword|semantic|hybrid`

### Integration test isolation
- SQLite: `data/integration.db` (separate from `data/memory.db`)
- Qdrant: `test_memory` collection (separate from `notes_embeddings`)
- QDRANT_COLLECTION patched at module level in: `app.db.qdrant`, `app.services.embedding_service`, `app.services.note_service`
- FTS5 table + triggers created in BOTH `init_db()` (production) and `seeded_client` fixture (integration test isolation)
- Session-scoped seeded data — 14 notes + 13 links created once, shared across all integration tests

### Full test layout
```
tests/
├── __init__.py
├── conftest.py                              # autouse mocks: embeddings + Qdrant (query_points)
├── test_services/
│   ├── test_schemas.py                      # 16 tests
│   ├── test_buffer_service.py               # 7 tests
│   ├── test_note_service.py                 # 6 tests
│   ├── test_tag_service.py                  # 4 tests
│   ├── test_link_and_relation_service.py    # 4 tests
│   └── test_search_service.py              # 3 tests
├── test_api/
│   ├── conftest.py                          # StaticPool engine, reset_db, client
│   ├── test_buffer.py                       # 8 tests
│   ├── test_notes.py                        # 11 tests
│   ├── test_tags.py                         # 4 tests
│   ├── test_relations.py                    # 6 tests
│   ├── test_export.py                       # 5 tests
│   └── test_admin.py                        # 3 tests
└── integration/
    ├── conftest.py                          # real Qdrant + Ollama, session-scoped seed
    ├── fixtures.py                          # 14 smart-home notes, 13 links, 5 buffer samples
    ├── test_seed.py                         # 7 tests
    ├── test_search_semantic.py              # 9 tests
    ├── test_search_keyword.py               # 7 tests
    ├── test_search_hybrid.py                # 5 tests
    ├── test_search_graph.py                 # 11 tests
    └── test_buffer.py                       # 9 tests
```
Total: **77 unit tests** + **48 integration tests** = 125 tests

### CLI reference
See `docs/cli-plan.md` for full command structure, project layout, and implementation order.

---

## Previous NEXT_SESSION.md Review

Previous items:
- **Phase 9 bash scripts** — likely dropped; CLI replaces them entirely
- **`docs/testing-plan.md` update** — still optional, not urgent
- **GitLab CI** — still future, homelab not active
