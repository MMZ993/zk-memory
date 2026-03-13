# Next Session — Pick Up Here

## Previous Session Summary

Go CLI implementation — skeleton + notes CRUD + buffer commands:

### Commits this session

- **`3216b9f`** — CLI skeleton: `go.mod` (cobra), `main.go`, `cmd/root.go`, `internal/client/client.go`, `internal/client/notes.go`, `cmd/notes.go` (all 6 notes subcommands + flags), stub cmd files for buffer/tags/relations/export/admin, `Makefile`
- **`d75d6a9`** — Buffer commands: `internal/client/buffer.go`, `cmd/buffer.go` (add, list, get, delete, process, cleanup)

### Go setup

- Go 1.26.1 installed via mise (`mise exec go -- go build`)
- cobra 1.10.2 (stdlib HTTP only, no extra HTTP deps)
- Binary builds to `cli/dist/memory` (gitignored)

### CLI state after this session

Fully implemented:
- `memory notes` — search, create, list, get, update, delete
- `memory buffer` — add, list (--processed/--unprocessed), get, delete, process, cleanup

Stubs only (no subcommands yet):
- `memory tags`
- `memory relations`
- `memory export`
- `memory admin`

---

## Remaining Tasks

### CLI (primary)

In order per `docs/cli-plan.md` step 5:

1. **`tags` global** — `list`, `create`
   - API: `GET /api/tags`, `POST /api/tags`
2. **`notes tags`** — `list`, `add`, `remove` (subcommand of notes)
   - API: `GET /api/notes/{id}/tags`, `POST /api/notes/{id}/tags`, `DELETE /api/notes/{id}/tags/{tag}`
3. **`notes links`** — `links`, `link`, `unlink`, `graph` (subcommands of notes)
   - API: `GET /api/notes/{id}/links`, `POST /api/notes/links`, `DELETE /api/notes/links/{link_id}`, `GET /api/notes/{id}/graph`
4. **`relations`** — `list`, `create`, `get`, `update`, `delete`
   - API: `GET/POST /api/relations`, `GET/PATCH/DELETE /api/relations/{id}`
5. **`export`** — `all`, `notes`, `buffer`
   - API: `GET /api/export/all`, `GET /api/export/notes`, `GET /api/export/buffer`
6. **`admin`** — `stats`, `config`, `sync`, `reembed`
   - API: `GET /api/admin/stats`, `GET /api/admin/config`, `POST /api/admin/sync-embeddings`, `POST /api/admin/reembed`
7. **Cross-compile + Makefile** — already done; add `make build-all` test
8. **`cli/README.md`** — usage guide per `docs/cli-plan.md`

### Future (not this repo)

- GitLab CI pipeline — homelab not active yet
- MCP server — after CLI complete, reuses `internal/client`

---

## Next Steps (prioritized)

1. **(Start now)** `tags global` + `notes tags` — `internal/client/tags.go` + expand `cmd/tags.go` + add tags subcommands to `cmd/notes.go`
2. `notes links` + `notes graph` — add link/graph subcommands to `cmd/notes.go`, `internal/client/notes.go` already has `Link` type
3. `relations` — `internal/client/relations.go` + `cmd/relations.go`
4. `export` — `internal/client/export.go` + `cmd/export.go`
5. `admin` — `internal/client/admin.go` + `cmd/admin.go`
6. `cli/README.md`

---

## Important Notes

### Building the CLI

```bash
cd cli/
mise exec go -- go build -o dist/memory .
# or if go is on PATH:
make build
```

### Running against local API

```bash
MEMORY_API_URL=http://localhost:8001 ./dist/memory notes list --pretty
```

### API status

- All 125 tests still passing (77 unit + 48 integration)
- Run unit: `source .venv/bin/activate && pytest tests/test_services/ tests/test_api/ -v`
- Run integration: `docker compose up qdrant -d && INTEGRATION_TESTS=1 pytest tests/integration/ -v`

### API endpoints still to implement in client

See `docs/api-specification.md` for exact request/response shapes. Key ones:

- `GET /api/tags` — returns `[{"id": ..., "name": ..., "note_count": ...}]`
- `POST /api/tags` — body `{"name": "tag-name"}`
- `GET /api/notes/{id}/tags` — returns array of tag objects
- `POST /api/notes/{id}/tags` — body `{"name": "tag-name"}`
- `DELETE /api/notes/{id}/tags/{tag_name}`
- `GET /api/notes/{id}/links?direction=all&limit=50`
- `POST /api/notes/links` — body `{"source_id": ..., "target_id": ..., "relation_type_id": ...}`
- `DELETE /api/notes/links/{link_id}`
- `GET /api/notes/{id}/graph?depth=1`
- Relations, export, admin — see spec

### Critical design constraints (do not break)

- **Two-phase sync**: notes written with `synced=False` → embedded → `synced=True`. Retry via `POST /api/admin/sync-embeddings`.
- **Route ordering**: `/api/notes/search` and `/api/notes/links` MUST stay before `/{note_id}`. `/api/buffer/cleanup` MUST stay before `/api/buffer/{note_id}`.
- **`client.query_points()` not `client.search()`** — qdrant-client removed `.search()`.
- **Search param is `search_type`** (not `mode`) — `?search_type=keyword|semantic|hybrid`

---

## Previous NEXT_SESSION.md Review

Previous top priority: "Implement the Go CLI"
- ✅ Skeleton done (go.mod, cobra root, internal/client base, Makefile)
- ✅ `notes search` + `notes create` — first two commands validating full stack
- ✅ Rest of `notes` CRUD (list, get, update, delete)
- ✅ `buffer` commands (add, list, get, delete, process, cleanup)
- ⏳ `tags`, `relations`, `export`, `admin` — next session

Other previous items:
- Bash scripts (`export_notes.sh`, `sync_back.sh`) — confirmed dropped; CLI replaces them
- `docs/testing-plan.md` update — still optional, not urgent
- GitLab CI — still future
