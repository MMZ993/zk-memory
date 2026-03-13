# CLI Dump Command — Design Plan

## Overview

`memory dump` exports notes to local files in a chosen format. Designed for:

- **Human browsing** — Obsidian vault, Wiki.js pages
- **Backups** — full or incremental JSON snapshots
- **Incremental sync** — only re-export notes changed since last dump

No API changes required. All data is available via existing endpoints.

---

## Command

```bash
memory dump \
  --output <dir> \
  [--format obsidian|json|wikijs] \
  [--since <ISO-8601-date>] \
  [--state <path>] \
  [--no-state] \
  [--force] \
  [--concurrency N]
```

### Flags

| Flag | Default | Description |
|---|---|---|
| `--output` | **required** | Output directory (created if absent) |
| `--format` | `obsidian` | Output format: `obsidian`, `json`, `wikijs` |
| `--since` | — | Only dump notes with `updated_at` after this date |
| `--state` | `<output>/.dump-state.json` | State file path |
| `--no-state` | `false` | Ignore state file (no read, no write) |
| `--force` | `false` | Overwrite existing dump even if format mismatches state |
| `--concurrency` | `5` | Parallel workers for per-note link fetching |

---

## State File

Saved to `<output>/.dump-state.json` after each successful run.

```json
{
  "dumped_at": "2026-03-13T15:00:00Z",
  "format": "obsidian",
  "stats": {
    "notes_dumped": 42,
    "notes_total": 42,
    "links": 67,
    "tags": 15
  }
}
```

### State file checks (run on every dump)

**1. No `--since` given + state file exists → use `dumped_at` as cutoff**

The state file's `dumped_at` becomes the implicit `--since`. No flag needed for
routine incremental syncs.

**2. Format mismatch → error (requires `--force` to override)**

If the state file records `"format": "obsidian"` but the current run uses
`--format wikijs`, the CLI exits with an error:

```
error: output directory was last dumped as "obsidian", requested format is "wikijs"
       use --force to overwrite, or choose a different --output directory
```

Rationale: mixing formats in one directory (e.g. Obsidian `.md` + Wiki.js `.md`)
produces a broken vault. `--force` acknowledges the user knows what they're doing.

**3. `--force` behaviour**

- Clears the format check, proceeds with the requested format
- Still writes a fresh state file after the run (with the new format recorded)
- Does NOT delete old files from the previous format — that's the user's responsibility

### Usage examples

```bash
# First full dump — saves state
memory dump --output ~/vault --format obsidian

# Next day — incremental (reads dumped_at from state, same format)
memory dump --output ~/vault

# Switch to wiki.js — blocked without --force
memory dump --output ~/vault --format wikijs
# → error: format mismatch

# Switch to wiki.js — forced
memory dump --output ~/vault --format wikijs --force

# One-off export with explicit date, no state read/write
memory dump --output /tmp/snapshot --since 2026-03-01 --no-state

# Manual cutoff, ignoring state file
memory dump --output ~/vault --since 2026-03-01
```

---

## Algorithm

```
1. Read state file (unless --no-state):
   a. If state file exists and --since not given → cutoff = state.dumped_at
   b. If state file exists and format != requested format:
        if --force → warn and continue
        else       → exit with error (format mismatch)
   c. If state file absent and --since not given → full dump (no cutoff)

2. GET /api/export/notes
   → all notes (tags included per export_service)
   → build: id → {title, updated_at} map  (needed to resolve link targets)

3. GET /api/relations
   → build: relation_type_id → name map

4. Filter notes where updated_at >= cutoff → to_dump
   (if no cutoff, to_dump = all notes)

5. For each note in to_dump (concurrent workers):
   a. GET /api/notes/{id}/links
   b. Resolve each link's target_id → title (from map built in step 2)
   c. Resolve each link's relation_type_id → name (from map built in step 3)
   d. Write file in chosen format

6. Write updated state file
```

**Request count**: `2 + len(to_dump)` — efficient for incremental runs.

---

## Output Formats

### obsidian

- One `.md` file per note, filename = sanitized title
- YAML frontmatter with id, tags, dates
- Links rendered as `[[Target Title]]` wikilinks with relation type as suffix

```markdown
---
id: 550e8400-e29b-41d4-a716-446655440000
title: "LSTM Notes"
tags: [ml, deep-learning]
created: 2026-01-15T10:00:00Z
updated: 2026-03-10T14:22:00Z
---

Content of the note here...

## Links

- [[Transformer Architecture]] — extends
- [[Attention Mechanisms]] — references
```

Filename collision (two notes with identical sanitized title): append `-<short-id>` suffix.

### json

- Single file `notes.json` (or per-note `<id>.json` — TBD, probably single file for simplicity)
- Each note object enriched with resolved link details

```json
[
  {
    "id": "550e8400-...",
    "title": "LSTM Notes",
    "content": "...",
    "summary": "...",
    "tags": ["ml", "deep-learning"],
    "created_at": "2026-01-15T10:00:00Z",
    "updated_at": "2026-03-10T14:22:00Z",
    "synced": true,
    "links": [
      {
        "id": "link-uuid",
        "target_id": "target-uuid",
        "target_title": "Transformer Architecture",
        "relation_type": "extends",
        "description": ""
      }
    ]
  }
]
```

Note: incremental mode for JSON format still writes the full file (replaces it), since
a partial JSON array is not useful.

### wikijs

- One `.md` file per note, filename = sanitized slug (lowercase, hyphens)
- YAML frontmatter compatible with Wiki.js page metadata
- Links rendered as standard Markdown links `[Title](/slug)`

```markdown
---
title: LSTM Notes
description: Summary text if present
tags:
  - ml
  - deep-learning
created: 2026-01-15
updated: 2026-03-10
---

Content of the note here...

## Related pages

- [Transformer Architecture](/transformer-architecture) — extends
- [Attention Mechanisms](/attention-mechanisms) — references
```

---

## API Findings

### What each endpoint returns

| Endpoint | Notes | Tags | Links | Relation type name |
|---|---|---|---|---|
| `GET /api/export/notes` | ✅ all | ✅ included | ❌ | n/a |
| `GET /api/notes/{id}/links` | n/a | n/a | ✅ | ❌ (id only) |
| `GET /api/relations` | n/a | n/a | n/a | ✅ |

### `LinkResponse` returns `relation_type_id` only — intentional

`LinkResponse` returns `relation_type_id` rather than embedding the full relation type
object. This is the correct design: there may be 100k+ links but only 10–20 relation
types. Embedding the full object in every link response would be redundant at scale.

The right pattern (used here) is: fetch `GET /api/relations` once per run, build an
`id → name` map, resolve locally. Cost: 1 extra request total.

The API spec's Link model showing a full embedded `relation_type` block is incorrect
and should be updated to show only `relation_type_id`.

### No `updated_after` filter on notes list

The `GET /api/notes` endpoint doesn't support `updated_after`. Client-side filtering
is used: fetch all notes, filter by `updated_at >= cutoff`. For typical homelab
datasets (hundreds to low thousands of notes), this is fast and simple.

**Future improvement** (optional): add `updated_after` query param to `GET /api/notes`.
Would allow fetching only changed notes without downloading all. Needed only if
datasets grow large enough that full-fetch becomes slow.

---

## New Files

```
cli/
├── cmd/dump.go                     # cobra command, flags, main orchestration
├── internal/
│   └── dump/
│       ├── dump.go                 # fetch, filter, write loop, state management
│       ├── state.go                # state file read/write
│       └── format/
│           ├── obsidian.go         # Obsidian .md writer
│           ├── json.go             # JSON writer (single file)
│           └── wikijs.go           # Wiki.js .md writer
```

The `dump` package imports `internal/client` but does not add new client methods —
it uses the existing `ExportNotes`, `ListRelations`, `GetNoteLinks` methods.

---

## No API changes required ✅

All required data is reachable via existing endpoints. The plan works today.
