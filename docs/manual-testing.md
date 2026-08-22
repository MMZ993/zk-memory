# Manual Testing Guide

Step-by-step instructions for spinning up the test stacks, seeding the smart-home dataset, and exercising the CLI against both the no-auth and auth-enabled servers.

---

## Prerequisites

```bash
# Python venv active
source .venv/bin/activate

# Ollama running with the embedding model pulled
ollama pull nomic-embed-text
ollama serve   # or let it run as a service

# CLI binary built
cd cli && go build -o dist/memory . && cd ..
export PATH="$PWD/cli/dist:$PATH"   # add to PATH for this session
```

---

## Stack A — No-auth (dev mode, port 8001)

This is the standard integration test stack. Auth is disabled — no `MEMORY_API_KEY_*` vars are set, so every request is accepted without a key.

### Start

```bash
docker compose -f docker-compose.test.yml up -d --build
```

Wait for the API to be ready (usually 5–10 seconds):

```bash
curl -s http://localhost:8001/api/health | python3 -m json.tool
```

Expected:
```json
{"status": "healthy", "version": "1.0.0"}
```

Use `/api/readiness` to verify database and Qdrant availability.

### Seed the dataset (14 notes + 13 links)

```bash
MEMORY_API_URL=http://localhost:8001 python3 - <<'EOF'
import httpx, sys
sys.path.insert(0, "tests")
from integration.fixtures import seed_data
ids = seed_data(httpx.Client(base_url="http://localhost:8001"))
print(f"Seeded {len(ids)} notes.")
for title, nid in ids.items():
    print(f"  {nid}  {title}")
EOF
```

Save the printed IDs — you'll use some of them in the commands below. Or just set the env var and use `notes list` to look them up.

### Environment

```bash
export MEMORY_API_URL=http://localhost:8001
# No key needed — auth is disabled
unset MEMORY_API_KEY
```

### Teardown

```bash
docker compose -f docker-compose.test.yml down -v
```

---

## Stack B — Auth-enabled (scoped keys, port 8003)

This stack has all five `MEMORY_API_KEY_*` vars configured with test keys.

| Scope  | Key               |
|--------|-------------------|
| READ   | `test_key_read`   |
| BUFFER | `test_key_buffer` |
| WRITE  | `test_key_write`  |
| DUMP   | `test_key_dump`   |
| ADMIN  | `test_key_admin`  |

### Start

```bash
docker compose -f docker-compose.test.auth.yml up -d --build
```

```bash
curl -s http://localhost:8003/api/health | python3 -m json.tool
```

### Seed the dataset

Auth is enabled, so the seed script needs the WRITE key (or ADMIN key):

```bash
MEMORY_API_URL=http://localhost:8003 python3 - <<'EOF'
import httpx, sys
sys.path.insert(0, "tests")
from integration.fixtures import seed_data
client = httpx.Client(
    base_url="http://localhost:8003",
    headers={"X-API-Key": "test_key_admin"},
)
ids = seed_data(client)
print(f"Seeded {len(ids)} notes.")
for title, nid in ids.items():
    print(f"  {nid}  {title}")
EOF
```

### Helper aliases (optional — scope routing made easy)

```bash
alias memory-read='MEMORY_API_URL=http://localhost:8003 MEMORY_API_KEY=test_key_read memory'
alias memory-write='MEMORY_API_URL=http://localhost:8003 MEMORY_API_KEY=test_key_write memory'
alias memory-buffer='MEMORY_API_URL=http://localhost:8003 MEMORY_API_KEY=test_key_buffer memory'
alias memory-dump='MEMORY_API_URL=http://localhost:8003 MEMORY_API_KEY=test_key_dump memory'
alias memory-admin='MEMORY_API_URL=http://localhost:8003 MEMORY_API_KEY=test_key_admin memory'
```

### Teardown

```bash
docker compose -f docker-compose.test.auth.yml down -v
```

---

## CLI command reference

All examples below use Stack A (`MEMORY_API_URL=http://localhost:8001`, no key).
For Stack B, prefix commands with the appropriate key alias or set `MEMORY_API_KEY=<key>`.

### Admin

```bash
# Health check
memory admin health --pretty

# System stats (note count, buffer count, synced %)
memory admin stats --pretty

# Active configuration
memory admin config --pretty

# Sync embeddings for any notes still pending (synced=false)
memory admin sync --pretty
```

### Notes — list and get

```bash
# List all notes (compact JSON)
memory notes list

# List with pretty output
memory notes list --pretty

# List with pagination
memory notes list --limit 5 --offset 0 --pretty

# List sorted by creation date descending
memory notes list --sort created_at --order desc --pretty

# Filter by tag
memory notes list --tags automation --pretty
memory notes list --tags lighting,bedroom --pretty

# Get a single note by ID (replace <id> with a real UUID from the list output)
NOTE_ID=$(memory notes list | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
memory notes get "$NOTE_ID" --pretty
```

### Notes — search

The dataset covers smart home topics (lights, thermostat, MQTT, Zigbee, Frigate, etc.).

```bash
# Semantic search — vector similarity
memory notes search "how do I automate morning lights" --mode semantic --pretty
memory notes search "energy consumption tracking" --mode semantic --limit 3 --pretty

# Keyword search — FTS5 / tsvector exact match
memory notes search "MQTT" --mode keyword --pretty
memory notes search "Zigbee" --mode keyword --pretty
memory notes search "Frigate" --mode keyword --pretty

# Hybrid search — semantic + keyword combined
memory notes search "security camera person detection" --mode hybrid --pretty

# Graph search — relationship traversal from best-matching note
memory notes search "morning routine" --mode graph --pretty

# Limit results and set score threshold
memory notes search "thermostat" --mode semantic --limit 5 --threshold 0.7 --pretty

# Search filtered to a tag
memory notes search "lights" --mode semantic --tags lighting --pretty
```

### Notes — create, update, delete

```bash
# Create a note
memory notes create \
  --title "Test Note" \
  --content "This is a manual test note for verifying write access." \
  --tags "test,manual" \
  --pretty

# Update a note (replace <id>)
memory notes update "$NOTE_ID" \
  --title "Updated Test Note" \
  --content "Updated content." \
  --pretty

# Delete a note
memory notes delete "$NOTE_ID"
```

### Notes — links and graph

```bash
# Get all links for a note
memory notes links list "$NOTE_ID" --pretty

# Get only outgoing links
memory notes links list "$NOTE_ID" --direction outgoing --pretty

# Get only incoming links
memory notes links list "$NOTE_ID" --direction incoming --pretty

# Graph traversal — all notes reachable within 1 hop
memory notes links graph "$NOTE_ID" --depth 1 --pretty

# Deeper traversal (up to 3 hops)
memory notes links graph "$NOTE_ID" --depth 2 --pretty

# Create a link between two notes
NOTE_A=$(memory notes list | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['id'])")
NOTE_B=$(memory notes list | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[1]['id'])")

memory notes links link \
  --source "$NOTE_A" \
  --target "$NOTE_B" \
  --relation-type "related_to" \
  --pretty

# Delete a link by its ID
LINK_ID=$(memory notes links list "$NOTE_A" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['id'])")
memory notes links unlink "$LINK_ID"
```

### Buffer

```bash
# Add a buffer note (fast write, no embedding)
memory buffer add --content "Remember to check Zigbee firmware" --pretty
memory buffer add --content "Look into Matter protocol" --source research --pretty
memory buffer add --content "High priority task" --meta '{"priority":"high","source":"voice"}' --pretty

# List only unprocessed (default)
memory buffer list --pretty

# List only processed
memory buffer list --processed --pretty

# List all buffer notes
memory buffer list --all --pretty

# Get one buffer note by ID
BUFFER_ID=$(memory buffer list | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
memory buffer get "$BUFFER_ID" --pretty

# Mark as processed (the calling agent decides when to promote to permanent note)
memory buffer process "$BUFFER_ID" --pretty

# Delete a buffer note
memory buffer delete "$BUFFER_ID"

# Clean up old processed notes (older than BUFFER_RETENTION_DAYS)
memory buffer cleanup --pretty
```

### Tags

```bash
# List all tags with usage counts
memory tags list --pretty
```

### Export / Dump

```bash
# Export all notes as JSON (raw API response)
memory export notes --pretty
memory export buffer --pretty

# Dump to Obsidian vault format
memory dump --output /tmp/memory-vault --format obsidian

# Dump to JSON files
memory dump --output /tmp/memory-json --format json

# Incremental dump (only notes changed since last run — uses state file)
memory dump --output /tmp/memory-vault --format obsidian
# Run again — only new/updated notes are written

# Force full re-dump ignoring state
memory dump --output /tmp/memory-vault --format obsidian --no-state

# Dump with explicit cutoff date
memory dump --output /tmp/memory-vault --format obsidian --since 2026-01-01
```

---

## Auth verification (Stack B)

Confirm that auth is correctly enforced. Use the aliases from above or set the key inline.

### Public endpoint — no key required

```bash
curl -s http://localhost:8003/api/health
# → 200 OK
```

### No key → 401

```bash
# Via CLI
MEMORY_API_URL=http://localhost:8003 unset MEMORY_API_KEY
MEMORY_API_URL=http://localhost:8003 memory notes list
# → error: API error 401: {"detail":"API key required"}
# exit code: 1

# Via curl
curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/api/notes/
# → 401
```

### Wrong scope → 403

```bash
# READ key trying to create a note
MEMORY_API_URL=http://localhost:8003 MEMORY_API_KEY=test_key_read \
  memory notes create --title "should fail" --content "write attempt with read key"
# → error: API error 403: {"detail":"API key does not have the required scope for this operation"}
# exit code: 1

# WRITE key trying to read export
MEMORY_API_URL=http://localhost:8003 MEMORY_API_KEY=test_key_write \
  memory export notes
# → error: API error 403: ...

# BUFFER key trying to list notes
MEMORY_API_URL=http://localhost:8003 MEMORY_API_KEY=test_key_buffer \
  memory notes list
# → error: API error 403: ...

# DUMP key trying to write
MEMORY_API_URL=http://localhost:8003 MEMORY_API_KEY=test_key_dump \
  memory notes create --title "should fail" --content "dump key write attempt"
# → error: API error 403: ...
```

### Correct scope → success

```bash
# READ key: list notes
memory-read notes list --pretty
# → JSON array of notes, exit code 0

# READ key: search
memory-read notes search "morning routine" --mode semantic --pretty
# → search results, exit code 0

# WRITE key: create note
memory-write notes create \
  --title "Auth Test Note" \
  --content "Created with write key to verify scope." \
  --pretty
# → 201, note JSON

# BUFFER key: add buffer entry
memory-buffer buffer add --content "Buffer entry via buffer key" --pretty
# → 201, buffer note JSON

# DUMP key: export
memory-dump export notes --pretty
# → JSON export of all notes

# ADMIN key: config
memory-admin admin config --pretty
# → current server configuration including embedding settings, DB backend, etc.
```

### Admin key bypasses all scope checks

```bash
# Admin key can do everything — READ, WRITE, BUFFER, DUMP, ADMIN all work
memory-admin notes list --pretty
memory-admin notes create --title "Admin write" --content "Written with admin key." --pretty
memory-admin buffer add --content "Admin buffer entry" --pretty
memory-admin export notes --pretty
memory-admin admin config --pretty
```

---

## Running automated tests

```bash
# Go unit tests — no external services needed
make test-cli

# Python unit tests — no external services needed
make test

# Integration tests (SQLite, port 8001)
make test-integration

# Integration tests (PostgreSQL, port 8002)
make test-integration-postgres

# Auth integration tests (port 8003) — builds CLI binary, runs test_auth.py
make test-integration-auth
```

---

## Scope reference

| Scope  | Key env var              | Allowed endpoints                                                           |
|--------|--------------------------|-----------------------------------------------------------------------------|
| READ   | `MEMORY_API_KEY_READ`    | GET notes, search, buffer list, tags, relations, stats                      |
| BUFFER | `MEMORY_API_KEY_BUFFER`  | POST /api/buffer/ (append only)                                             |
| WRITE  | `MEMORY_API_KEY_WRITE`   | POST/PATCH/DELETE notes, links, tags, relations; buffer process/delete      |
| DUMP   | `MEMORY_API_KEY_DUMP`    | GET /api/export/, /api/export/notes, /api/export/buffer                     |
| ADMIN  | `MEMORY_API_KEY_ADMIN`   | GET /api/config, POST /api/admin/reembed, admin/sync — and all of the above |
| —      | (none set)               | Auth disabled — all endpoints open (dev mode)                               |

See `docs/api-scopes.md` for the full endpoint-to-scope mapping.
