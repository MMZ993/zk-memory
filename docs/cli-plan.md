# CLI Tool — Planning Document

## Overview

A Go binary CLI that acts as the primary frontend to the FastAPI memory system.
Agents and humans interact with the memory system through this CLI, not by calling the API directly.

## Deployment Context

- **API lives on**: homelab VM (Docker: FastAPI + Qdrant)
- **CLI lives on**: agent VM (or any machine that can reach the API)
- **Two environments**: PROD and TEST — same CLI binary, different `MEMORY_API_URL`
- **Release flow**: TEST VM → run integration tests → pass → promote to PROD

## Language: Go

Single static binary. No runtime dependencies. Copy to any VM and run.
Cross-compile for `linux/amd64` and `linux/arm64` from one machine.

## Configuration (ENV vars only)

```bash
MEMORY_API_URL=http://192.168.1.10:8080   # required
MEMORY_API_KEY=secret123                   # optional, sent as X-API-Key header
MEMORY_TIMEOUT=30                          # optional, seconds, default 30
```

Agent sets these before invoking the CLI (export in `.bashrc` or inline).
No config file, no `init` command needed.

## Output Format

- **Default**: JSON (compact, agent-friendly, parseable)
- **`--pretty` / `-p` flag**: human-readable tables with formatting

Global `--pretty` flag on root command, inherited by all subcommands.
All errors → stderr + exit code 1. Success → stdout + exit code 0.

## Framework

- **CLI**: [`cobra`](https://github.com/spf13/cobra) — industry standard for multi-command Go CLIs
- **HTTP**: stdlib `net/http` + `encoding/json` — no extra dependencies needed

## Command Structure (1:1 with API)

```
memory
├── notes
│   ├── list        [--tags x,y] [--sort updated_at|created_at] [--order asc|desc] [--limit N] [--offset N]
│   ├── create      --title "..." --content "..." [--tags x,y] [--summary "..."]
│   ├── get         <id>
│   ├── update      <id> [--title "..."] [--content "..."] [--summary "..."] [--tags x,y]
│   ├── delete      <id>
│   ├── search      --query "..." [--mode semantic|keyword|hybrid] [--limit N] [--threshold 0.7] [--tags x,y]
│   ├── graph       <id> [--depth N]
│   ├── links       <id>
│   ├── link        --from <id> --to <id>
│   ├── unlink      <link-id>
│   └── tags
│       ├── list    <note-id>
│       ├── add     <note-id> <tag>
│       └── remove  <note-id> <tag>
├── buffer
│   ├── list        [--processed] [--limit N] [--offset N]
│   ├── add         --content "..." [--source "..."] [--meta '{"key":"val"}']
│   ├── get         <id>
│   ├── delete      <id>
│   ├── process     <id>
│   └── cleanup
├── tags
│   ├── list        [--limit N]
│   └── create      --name "..."
├── relations
│   ├── list        [--limit N]
│   ├── create      --from <id> --to <id> --type <type> [--note "..."]
│   ├── get         <id>
│   ├── update      <id> [--note "..."]
│   └── delete      <id>
├── export
│   ├── all
│   ├── notes
│   └── buffer
└── admin
    ├── stats
    ├── config
    ├── sync
    └── reembed     --confirm "I understand this will delete and regenerate all embeddings"
```

## Project Layout

```
cli/
├── cmd/
│   ├── root.go          # cobra root command, global flags, HTTP client init
│   ├── notes.go         # all notes subcommands
│   ├── buffer.go        # all buffer subcommands
│   ├── tags.go
│   ├── relations.go
│   ├── export.go
│   └── admin.go
├── internal/
│   └── client/
│       ├── client.go    # base HTTP client (auth header, timeout, base URL, error handling)
│       ├── notes.go     # typed methods for notes API
│       ├── buffer.go    # typed methods for buffer API
│       ├── tags.go
│       ├── relations.go
│       ├── export.go
│       └── admin.go
├── main.go
├── go.mod
├── go.sum
├── Makefile             # build + cross-compile targets
└── README.md
```

## Makefile Targets

```makefile
build:
    GOOS=linux GOARCH=amd64 go build -o dist/memory-linux-amd64 .
    GOOS=linux GOARCH=arm64 go build -o dist/memory-linux-arm64 .

test:
    go test ./...
```

## Future: MCP Server

The `internal/client` package is the shared API client library.
The MCP server will be a second binary importing the same package:

```
cli/main.go  → imports internal/client → cobra CLI presentation
mcp/main.go  → imports internal/client → MCP tool handlers
```

One API client, two frontends. MCP server does NOT subprocess-call the CLI binary.

## Future: Scripts

With a complete CLI, the planned `scripts/export_notes.sh` and `scripts/sync_back.sh`
become one-liners using the CLI. Scripts folder may be dropped entirely.

## Future: Skills

Two planned Claude Code skills:
1. **Memory reader/writer** — `notes search`, `buffer add` (read memory, capture ideas)
2. **Dreamer** — `buffer list`, `buffer process`, `notes create`, `notes search`, `relations create` (consolidate buffer into structured notes with tags and links)

Skills will be designed after CLI is complete and tested.

## Implementation Order

1. `go.mod` + project skeleton + `internal/client` base HTTP client
2. `notes search` + `notes create` (core agent operations, validates the whole stack)
3. Rest of `notes` CRUD
4. `buffer` commands
5. `tags`, `relations`, `export`, `admin`
6. `--pretty` output for all commands
7. Cross-compile + Makefile
