# Backup Strategy

Backup is handled externally. This project does not expose backup API endpoints. Both data stores are files/directories that can be backed up with standard tools.

## SQLite

SQLite is a single file: `data/memory.db`.

**Backup**: Copy the file. Use SQLite's online backup API if copying while the server is running:

```bash
# Simple file copy (safe when server is stopped)
cp data/memory.db data/backups/memory_$(date +%Y%m%d_%H%M%S).db

# Online backup using sqlite3 (safe while server is running)
sqlite3 data/memory.db ".backup data/backups/memory_$(date +%Y%m%d_%H%M%S).db"
```

**Restore**: Stop the server, replace `data/memory.db`, restart.

## Qdrant

Qdrant stores all data in the `qdrant_storage/` directory (mounted as a Docker volume).

### Option A: Directory copy (simplest, requires stopping Qdrant)

```bash
# Stop Qdrant
docker compose stop qdrant

# Copy storage directory
cp -r qdrant_storage/ qdrant_storage_backup_$(date +%Y%m%d_%H%M%S)/

# Restart
docker compose start qdrant
```

### Option B: Qdrant native snapshot API (live, no downtime)

```bash
# Create snapshot
curl -X POST http://localhost:6333/collections/notes_embeddings/snapshots

# List snapshots
curl http://localhost:6333/collections/notes_embeddings/snapshots

# Download snapshot (snapshots are stored in qdrant_storage/snapshots/)
```

**Restore**: Use `POST /collections/{name}/snapshots/recover` or replace the storage directory when stopped.

## Consistency

To ensure SQLite and Qdrant are consistent at restore time, back them up at the same time. Any notes in SQLite with `synced=false` are safe — they will be re-embedded on the next `POST /api/admin/sync-embeddings` call.

## Automated Backup Example

```bash
#!/bin/bash
# Simple daily backup script — run via cron or external scheduler

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./data/backups"

mkdir -p "$BACKUP_DIR"

# SQLite
sqlite3 data/memory.db ".backup ${BACKUP_DIR}/memory_${TIMESTAMP}.db"
echo "SQLite backed up to ${BACKUP_DIR}/memory_${TIMESTAMP}.db"

# Qdrant snapshot
curl -s -X POST http://localhost:6333/collections/notes_embeddings/snapshots
echo "Qdrant snapshot created (see qdrant_storage/snapshots/)"
```
