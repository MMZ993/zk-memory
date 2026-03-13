# memory CLI

Go CLI for the AI agent memory system. Single static binary, no runtime dependencies.

## Installation

Build from source (requires Go 1.22+):

```bash
cd cli/
make build           # linux/amd64 → dist/memory
make build-all       # cross-compile linux/amd64 + linux/arm64
```

Copy the binary to any machine that can reach the API:

```bash
cp dist/memory /usr/local/bin/memory
```

## Configuration

Set environment variables before running. No config file needed.

| Variable | Required | Default | Description |
|---|---|---|---|
| `MEMORY_API_URL` | yes | — | API base URL, e.g. `http://192.168.1.10:8080` |
| `MEMORY_API_KEY` | no | — | Sent as `X-API-Key` header if set |
| `MEMORY_TIMEOUT` | no | `30` | HTTP timeout in seconds |

```bash
export MEMORY_API_URL=http://192.168.1.10:8080
export MEMORY_API_KEY=secret123
```

## Output

- **Default**: compact JSON (agent/pipe-friendly)
- **`--pretty` / `-p`**: indented JSON (or formatted text for some commands)

All errors go to stderr with exit code 1. Success goes to stdout with exit code 0.

## Commands

### notes

```bash
memory notes list [--tags x,y] [--sort created_at|updated_at] [--order asc|desc] [--limit N] [--offset N]
memory notes create --title "..." --content "..." [--summary "..."] [--tags x,y]
memory notes get <id>
memory notes update <id> [--title "..."] [--content "..."] [--summary "..."] [--tags x,y]
memory notes delete <id>
memory notes search <query> [--mode semantic|keyword|hybrid] [--limit N] [--threshold 0.7] [--tags x,y]
```

#### notes tags

```bash
memory notes tags list <note-id>
memory notes tags add <note-id> <tag-name>
memory notes tags remove <note-id> <tag-id>    # tag-id is UUID
```

#### notes links

```bash
memory notes links list <note-id> [--direction incoming|outgoing|all] [--limit N]
memory notes links link --source <id> --target <id> --relation-type <name> [--description "..."]
memory notes links unlink <link-id>
memory notes links graph <note-id> [--depth 1]
```

### buffer

```bash
memory buffer add --content "..." [--source "label"] [--meta '{"key":"val"}']
memory buffer list [--processed] [--unprocessed] [--limit N] [--offset N]
memory buffer get <id>
memory buffer delete <id>
memory buffer process <id>
memory buffer cleanup
```

### tags

```bash
memory tags list [--limit N] [--offset N]
memory tags create <name>
```

### relations

Manage relation types (used to label links between notes).

```bash
memory relations list
memory relations create --name <name> [--description "..."] [--bidirectional]
memory relations get <id>
memory relations update <id> [--name "..."] [--description "..."] [--bidirectional]
memory relations delete <id>
```

### export

Export returns JSON arrays. Redirect to a file to save.

```bash
memory export all > backup.json
memory export notes > notes.json
memory export buffer > buffer.json
```

### dump

Export notes to local files for human browsing or backup.

```bash
# Full dump to Obsidian vault (default format)
memory dump --output ~/vault

# Incremental: subsequent runs auto-use last dump date from state file
memory dump --output ~/vault

# Other formats
memory dump --output ~/wiki --format wikijs
memory dump --output ~/backup --format json

# Explicit date cutoff
memory dump --output ~/vault --since 2026-03-01

# Force format change (clears format-mismatch error)
memory dump --output ~/vault --format wikijs --force

# Skip state file entirely (one-off snapshot)
memory dump --output /tmp/snapshot --no-state
```

**State file** (`<output>/.dump-state.json`): saved after each run with `dumped_at`, `format`, and stats. On the next run without `--since`, `dumped_at` becomes the implicit cutoff — only notes updated since the last dump are written.

**Format mismatch**: if the state file records a different format than requested, the command exits with an error. Use `--force` to override (does not delete old format files).

| Flag | Default | Description |
|---|---|---|
| `--output` | required | Output directory |
| `--format` | `obsidian` | `obsidian` \| `json` \| `wikijs` |
| `--since` | — | ISO 8601 date cutoff |
| `--state` | `<output>/.dump-state.json` | State file path |
| `--no-state` | false | Skip state file entirely |
| `--force` | false | Override format mismatch |
| `--concurrency` | 5 | Parallel link-fetch workers |

### admin

```bash
memory admin health
memory admin stats
memory admin config
memory admin sync
memory admin reembed start --confirm    # destructive: deletes + regenerates all embeddings
memory admin reembed status
```

## Examples

```bash
# Search for notes about ML
memory notes search "machine learning" --mode hybrid --limit 10 --pretty

# Create a note with tags
memory notes create --title "LSTM Notes" --content "..." --tags ml,deep-learning

# Add a quick thought to the buffer
memory buffer add --content "Look into LoRA for fine-tuning" --source agent

# Link two notes
memory notes links link --source <id1> --target <id2> --relation-type "extends"

# Walk the knowledge graph from a note
memory notes links graph <id> --depth 2 --pretty

# Export everything and save
MEMORY_API_URL=http://prod:8080 memory export all > backup-$(date +%F).json

# Check system health
memory admin health --pretty
memory admin stats --pretty
```

## Project layout

```
cli/
├── cmd/              # cobra commands (one file per top-level command)
├── internal/
│   └── client/       # typed HTTP client (reused by future MCP server)
├── main.go
├── go.mod
└── Makefile
```
