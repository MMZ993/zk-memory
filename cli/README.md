# memory CLI

Go CLI for the AI agent memory system. Single static binary, no runtime dependencies.

## Installation

Build from source (requires Go 1.26+):

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

### Scoped access via bash functions

The API enforces per-scope keys (see [`../docs/api-scopes.md`](../docs/api-scopes.md)). The CLI sends a single key per invocation, so when multiple agents share the same machine each with a different role, define bash functions in `.bashrc` to pin the right key per role:

```bash
memory_read()   { MEMORY_API_KEY=key_ro_xxx   memory "$@"; }
memory_buffer() { MEMORY_API_KEY=key_buf_xxx  memory "$@"; }
memory_write()  { MEMORY_API_KEY=key_rw_xxx   memory "$@"; }
memory_dump()   { MEMORY_API_KEY=key_dump_xxx memory "$@"; }
memory_admin()  { MEMORY_API_KEY=key_adm_xxx  memory "$@"; }
```

Usage is identical to the binary:

```bash
memory_read   notes search "something" --pretty
memory_buffer buffer add --content "..."
memory_write  notes create --title "..."
memory_admin  admin stats --pretty
```

An agent needing two scopes (e.g. the overnight write agent that reads then writes) simply calls the appropriate function per operation:

```bash
memory_read  notes list                   # read phase
memory_write notes create --title "..."   # write phase
memory_write buffer process <id>
```

Using a key outside its configured scope returns `403: API key does not have the required scope for this operation`.

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
memory buffer list [--processed|--unprocessed|--all] [--limit N] [--offset N]  # defaults to --processed
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

`export all` returns the authoritative versioned JSON snapshot. It preserves IDs and timestamps and separately includes notes, tags, note-tag associations, relation types, links, and buffer notes. Redirect it to a file to save the snapshot. The resource-specific commands remain available and return JSON arrays.

```bash
memory export all > backup.json
memory export notes > notes.json
memory export buffer > buffer.json
```

### import

Canonical JSON imports require an admin API key and are dry-run by default. The report lists new, identical, conflicting, rejected/overwritten, and database-only entities. Applying an import never deletes database records.

```bash
memory import backup.json                         # dry-run only
memory import backup.json --soft                  # create clean entities, reject conflicts
memory import backup.json --force                 # overwrite matching-ID conflicts
memory import backup.json --type notes --id <id>  # analyze one entity
memory import backup.json --soft --type links --id <link-id>
memory import ~/vault                              # generated Obsidian/Wiki.js vault
memory import ~/vault/<note-id>.md --type notes --id <note-id>
memory import ~/vault/<note-id>.md --type links --id <link-id>
```

Supported JSON selection types are `notes`, `tags`, `note_tags`, `relation_types`, `links`, and `buffer_notes`. A note-tag ID is written as `<note-id>:<tag-id>`. `--soft` and `--force` are mutually exclusive.

Generated Markdown vault imports use note frontmatter and `zk-memory-manifest.json` as authoritative metadata; rendered Links/Related sections are ignored as note content. A lone generated Markdown file can supply its note and encoded links. Its tags reuse case-insensitive name matches from the database and receive deterministic IDs only when new. Shared relation types require the full vault manifest unless sufficient encoded dependency metadata is present; unsupported metadata is omitted rather than guessed.

### dump

Export notes to local files for human browsing or backup.

```bash
# Full dump to Obsidian vault (default format)
memory dump --output ~/vault

# Incremental: subsequent runs compare content inventory and only rewrite changes
memory dump --output ~/vault

# Other formats
memory dump --output ~/wiki --format wikijs
memory dump --output ~/backup --format json  # writes ~/backup/export.json

# Explicit date cutoff
memory dump --output ~/vault --since 2026-03-01

# Force format change (clears format-mismatch error)
memory dump --output ~/vault --format wikijs --force

# Skip state file entirely (one-off snapshot)
memory dump --output /tmp/snapshot --no-state
```

**Markdown layout and state**: notes use stable `<id>.md` paths, buffered items use `buffer/<id>.md`, and `zk-memory-manifest.json` stores versioned shared tag, note-tag, and relation metadata. Generated link sections are explicitly marked. `.dump-state.json` stores content hashes so subsequent runs only rewrite changed files and remove stale managed files. JSON dumps always replace `export.json` with a complete canonical snapshot.

**Format mismatch**: if the state file records a different format than requested, the command exits with an error. Use `--force` to override (does not delete old format files).

| Flag | Default | Description |
|---|---|---|
| `--output` | required | Output directory |
| `--format` | `obsidian` | `obsidian` \| `json` \| `wikijs` |
| `--since` | — | Accepted for compatibility; full inventory comparison determines Markdown changes |
| `--state` | `<output>/.dump-state.json` | State file path |
| `--no-state` | false | Skip state file entirely |
| `--force` | false | Override format mismatch |

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
