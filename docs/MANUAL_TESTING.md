# Manual Testing Guide — PostgreSQL Stack

Step-by-step instructions to start the stack with PostgreSQL, load seed data, and exercise the CLI.

---

## Prerequisites

- Docker + Docker Compose
- Go 1.22+ (for CLI build)
- Ollama running on the host with `nomic-embed-text` pulled:
  ```bash
  ollama pull nomic-embed-text
  ```
- (Optional) `OPENAI_API_KEY` env var if you switch `EMBEDDING_PROVIDER=openai` in `docker-compose.postgres.yml`

---

## 1. Start the PostgreSQL stack

```bash
# From the project root
docker compose -f docker-compose.postgres.yml up -d --build
```

Services started:
| Container | Port | Purpose |
|---|---|---|
| `agents-memory` | 8000 | FastAPI REST API |
| `postgres` | 5432 | PostgreSQL 16 |
| `qdrant` | 6333 | Vector search |

Wait for healthy status:
```bash
docker compose -f docker-compose.postgres.yml ps
# agents-memory should show "Up" (waits for postgres healthcheck)
```

Verify the API is up:
```bash
curl http://localhost:8000/api/health
# Expected: {"status":"ok"}
```

---

## 2. Seed the database with example notes

The seed script loads 14 notes (home automation domain) with links and tags:

```bash
source .venv/bin/activate

python - <<'EOF'
import httpx, sys
sys.path.insert(0, "tests")
from integration.fixtures import seed_data
seed_data(httpx.Client(base_url="http://localhost:8000"))
print("Seeded 14 notes and 13 links.")
EOF
```

---

## 3. Build the CLI

```bash
cd cli && go build -o dist/memory . && cd ..
```

Set the API URL for all CLI commands in this session:
```bash
export MEMORY_API_URL=http://localhost:8000
```

---

## 4. CLI verification commands

### Health and stats

```bash
# Check API health
cli/dist/memory admin health --pretty

# System stats (note count, tag count, etc.)
cli/dist/memory admin stats --pretty

# Full config (no secrets exposed)
cli/dist/memory admin config --pretty
```

### List notes

```bash
# List all notes (compact JSON — agent-friendly)
cli/dist/memory notes list

# Pretty-printed
cli/dist/memory notes list --pretty

# Only 3 notes, newest first
cli/dist/memory notes list --limit 3 --sort updated_at --order desc --pretty
```

### Search

```bash
# Keyword search (FTS — PostgreSQL tsvector)
cli/dist/memory notes search "mqtt" --mode keyword --pretty

# Semantic search (Qdrant embeddings)
cli/dist/memory notes search "wake up in the morning" --mode semantic --limit 5 --pretty

# Hybrid search (keyword + semantic, merged)
cli/dist/memory notes search "home automation" --mode hybrid --limit 5 --pretty

# Filter by tag
cli/dist/memory notes search "lighting" --mode hybrid --tags automation --pretty
```

### Create, update, delete

```bash
# Create a note
NOTE_ID=$(cli/dist/memory notes create \
  --title "Test Note" \
  --content "This is a manually created test note for verification." \
  --summary "Test" \
  --tags test,manual | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Created note: $NOTE_ID"

# Get it
cli/dist/memory notes get "$NOTE_ID" --pretty

# Update it
cli/dist/memory notes update "$NOTE_ID" --title "Updated Test Note" --pretty

# Delete it
cli/dist/memory notes delete "$NOTE_ID"
```

### Tags

```bash
# List all tags with note counts
cli/dist/memory tags list --pretty

# Create a new tag
cli/dist/memory tags create "verification"
```

### Links and knowledge graph

```bash
# Get the ID of the first note
FIRST_ID=$(cli/dist/memory notes list --limit 1 | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")

# List outgoing links from that note
cli/dist/memory notes links list "$FIRST_ID" --direction outgoing --pretty

# Walk the graph 2 hops deep
cli/dist/memory notes links graph "$FIRST_ID" --depth 2 --pretty
```

### Buffer

```bash
# Add a buffer note (fast write, no embedding)
BUF_ID=$(cli/dist/memory buffer add \
  --content "Quick thought: check MQTT retain flag behaviour" \
  --source "manual-test" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Buffer note: $BUF_ID"

# List unprocessed buffer notes
cli/dist/memory buffer list --unprocessed --pretty

# Mark as processed
cli/dist/memory buffer process "$BUF_ID"

# Confirm it moved to processed
cli/dist/memory buffer list --processed --pretty
```

### Dump to local files

```bash
# Dump all notes to /tmp/vault in Obsidian format
cli/dist/memory dump --output /tmp/vault --format obsidian --no-state

# Check the output
ls /tmp/vault/
head /tmp/vault/*.md | head -30
```

### Export (JSON backup)

```bash
# Full export to stdout
cli/dist/memory export all | python3 -m json.tool | head -50

# Save to file
cli/dist/memory export notes > /tmp/notes-backup.json
echo "Notes backed up: $(python3 -c "import json; d=json.load(open('/tmp/notes-backup.json')); print(len(d))")"
```

---

## 5. Verify PostgreSQL-specific behaviour

These checks confirm you're running against PostgreSQL (not SQLite).

```bash
# Should show DB_BACKEND=postgres in config
cli/dist/memory admin config --pretty | grep -i backend

# Keyword search uses tsvector (PostgreSQL FTS) — confirm results match
cli/dist/memory notes search "zigbee" --mode keyword --pretty
cli/dist/memory notes search "grafana" --mode keyword --pretty
cli/dist/memory notes search "frigate" --mode keyword --pretty
```

---

## 6. Tear down

```bash
# Stop and remove containers + volumes
docker compose -f docker-compose.postgres.yml down -v
```

To wipe and restart with a clean DB without removing volumes:
```bash
./scripts/dev-reset-postgres.sh
```

---

## Test summary

| Layer | Command | Expected |
|---|---|---|
| Unit (77) | `make test` | 77 passed |
| Integration SQLite (48) | `make test-integration` | 48 passed |
| Integration PostgreSQL (48) | `make test-integration-postgres` | 48 passed |
| CLI Go unit | `make test-cli` | ok |

Total: **173 tests, all passing.**
