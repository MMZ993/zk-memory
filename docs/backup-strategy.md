# Backup Strategy

Comprehensive backup and disaster recovery plan for AI Agent Memory System.

## Overview

This system stores data in two places:
1. **SQLite Database** (`memory.db`) - Structured data (notes, links, tags)
2. **Qdrant Vector Store** - Embeddings for semantic search

Both must be backed up together to maintain consistency.

## Backup Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Backup System                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │           SQLite Backup                          │  │
│  │  • Full database dump (SQL)                    │  │
│  │  • Incremental backup (optional)               │  │
│  │  • Stored in: ./data/backups/                  │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │           Qdrant Snapshot                       │  │
│  │  • Collection snapshot (vectors + payload)     │  │
│  │  • Managed by Qdrant API                       │  │
│  │  • Stored in Qdrant storage                    │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  Backup Coordinator                                      │
│  • Ensure atomicity (both or none)                       │
│  • Track backup metadata                                 │
│  • Automatic cleanup of old backups                      │
└─────────────────────────────────────────────────────────┘
```

## Backup Types

### 1. Full Backup

Creates complete backup of both SQLite and Qdrant.

**When**: Daily (configurable)

**Content**:
- SQLite database dump (`.db` file)
- Qdrant collection snapshot

**Retention**: 30 days (configurable via `BACKUP_RETENTION_DAYS`)

**Example**:
```bash
POST /api/admin/backup
{
  "name": "backup_20240120_143000"  // Optional, auto-generated if not provided
}
```

### 2. Incremental Backup (Future Enhancement)

Stores only changes since last backup.

**When**: Every 6 hours

**Content**:
- SQLite WAL file or transaction log
- Qdrant point updates

**Note**: Not implemented in MVP, planned for v2

### 3. On-Demand Backup

Manual backup triggered by user or before major operations.

**When**:
- Before re-embedding all notes
- Before schema migrations
- Before database maintenance

## Backup Implementation

### SQLite Backup

```python
# app/services/backup_service.py

import sqlite3
import shutil
from datetime import datetime
import os
from pathlib import Path

BACKUP_DIR = os.getenv("BACKUP_DIR", "./data/backups")
DATABASE_PATH = os.getenv("DATABASE_PATH", "./data/memory.db")

def create_sqlite_backup(backup_name: str = None) -> str:
    """Create SQLite database backup."""
    if not backup_name:
        backup_name = f"memory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

    backup_path = os.path.join(BACKUP_DIR, backup_name)

    # Ensure backup directory exists
    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)

    # Method 1: Copy file (simpler, works with WAL mode)
    shutil.copy2(DATABASE_PATH, backup_path)

    # Method 2: SQLite backup API (more robust)
    # conn = sqlite3.connect(DATABASE_PATH)
    # backup_conn = sqlite3.connect(backup_path)
    # conn.backup(backup_conn)
    # conn.close()
    # backup_conn.close()

    return backup_path

def restore_sqlite_backup(backup_path: str) -> bool:
    """Restore SQLite database from backup."""
    try:
        # Stop application (graceful shutdown)
        # (handled by API layer)

        # Replace current database
        shutil.copy2(backup_path, DATABASE_PATH)

        # Restart application
        # (handled by API layer)

        return True
    except Exception as e:
        print(f"Restore failed: {e}")
        return False

def list_sqlite_backups() -> list:
    """List all SQLite backups."""
    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)

    backups = []
    for file in Path(BACKUP_DIR).glob("memory_*.db"):
        stat = file.stat()
        backups.append({
            "name": file.name,
            "path": str(file),
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat()
        })

    return sorted(backups, key=lambda x: x["created_at"], reverse=True)

def delete_old_sqlite_backups(retention_days: int = 30) -> int:
    """Delete backups older than retention period."""
    cutoff = datetime.now() - timedelta(days=retention_days)
    deleted = 0

    for backup in list_sqlite_backups():
        backup_time = datetime.fromisoformat(backup["created_at"])
        if backup_time < cutoff:
            os.remove(backup["path"])
            deleted += 1

    return deleted
```

### Qdrant Backup

```python
# app/services/backup_service.py (continued)

from app.db.qdrant import client, QDRANT_COLLECTION
import uuid

def create_qdrant_snapshot() -> str:
    """Create Qdrant collection snapshot."""
    snapshot_info = client.create_snapshot(
        collection_name=QDRANT_COLLECTION
    )

    # Snapshot name looks like: "snapshot-20240120-143000-xxxx"
    snapshot_name = snapshot_info.name

    return snapshot_name

def restore_qdrant_snapshot(snapshot_name: str) -> bool:
    """Restore Qdrant collection from snapshot."""
    try:
        client.recover_snapshot(
            collection_name=QDRANT_COLLECTION,
            snapshot_name=snapshot_name
        )
        return True
    except Exception as e:
        print(f"Qdrant restore failed: {e}")
        return False

def list_qdrant_snapshots() -> list:
    """List all Qdrant snapshots."""
    snapshots = client.list_snapshots(collection_name=QDRANT_COLLECTION)

    return [
        {
            "name": snapshot.name,
            "created_at": snapshot.creation_time.isoformat(),
            "size_mb": round(snapshot.size / (1024 * 1024), 2)
        }
        for snapshot in snapshots
    ]

def delete_old_qdrant_snapshots(retention_days: int = 30) -> int:
    """Delete snapshots older than retention period."""
    cutoff = datetime.now() - timedelta(days=retention_days)
    deleted = 0

    for snapshot in list_qdrant_snapshots():
        snapshot_time = datetime.fromisoformat(snapshot["created_at"])
        if snapshot_time < cutoff:
            client.delete_snapshot(
                collection_name=QDRANT_COLLECTION,
                snapshot_name=snapshot["name"]
            )
            deleted += 1

    return deleted
```

### Backup Coordinator

```python
# app/services/backup_service.py (continued)

from sqlalchemy.orm import Session
from app.models.database import Metadata

def create_coordinated_backup(db: Session, backup_name: str = None) -> dict:
    """Create atomic backup of both SQLite and Qdrant."""
    if not backup_name:
        backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        # Step 1: Create SQLite backup
        sqlite_path = create_sqlite_backup(f"{backup_name}.db")

        # Step 2: Create Qdrant snapshot
        qdrant_snapshot = create_qdrant_snapshot()

        # Step 3: Record backup metadata
        backup_metadata = {
            "backup_id": backup_name,
            "sqlite_path": sqlite_path,
            "qdrant_snapshot": qdrant_snapshot,
            "created_at": datetime.now().isoformat()
        }

        # Store in metadata table (optional, or just file system)
        metadata = db.query(Metadata).filter(Metadata.key == "latest_backup").first()
        if not metadata:
            metadata = Metadata(key="latest_backup", value="")
        metadata.value = str(backup_metadata)
        db.add(metadata)
        db.commit()

        return backup_metadata

    except Exception as e:
        # Rollback: delete partial backup
        if "sqlite_path" in locals():
            os.remove(sqlite_path)
        if "qdrant_snapshot" in locals():
            try:
                client.delete_snapshot(
                    collection_name=QDRANT_COLLECTION,
                    snapshot_name=qdrant_snapshot
                )
            except:
                pass

        raise Exception(f"Backup failed: {e}")

def restore_coordinated_backup(db: Session, backup_id: str) -> bool:
    """Restore from coordinated backup."""
    try:
        # Get backup metadata
        metadata = db.query(Metadata).filter(Metadata.key == backup_id).first()
        if not metadata:
            raise Exception(f"Backup {backup_id} not found")

        backup_data = eval(metadata.value)

        # Step 1: Restore SQLite
        if not restore_sqlite_backup(backup_data["sqlite_path"]):
            raise Exception("SQLite restore failed")

        # Step 2: Restore Qdrant
        if not restore_qdrant_snapshot(backup_data["qdrant_snapshot"]):
            raise Exception("Qdrant restore failed")

        return True

    except Exception as e:
        raise Exception(f"Restore failed: {e}")

def list_backups(db: Session) -> list:
    """List all coordinated backups."""
    backups = db.query(Metadata).filter(Metadata.key.like("backup_%")).all()

    return [
        eval(m.value)
        for m in backups
    ]
```

## API Endpoints

### Create Backup

```python
# app/api/admin.py

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.backup_service import create_coordinated_backup, list_backups
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.post("/backup")
async def create_backup(
    name: str = None,
    db: Session = Depends(get_db)
):
    """Create coordinated backup."""
    try:
        backup = create_coordinated_backup(db, name)
        logger.info(f"Created backup: {backup['backup_id']}")
        return backup
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/backups")
async def list_all_backups(db: Session = Depends(get_db)):
    """List all backups."""
    backups = list_backups(db)
    return {"backups": backups}

@router.post("/restore/{backup_id}")
async def restore_backup(
    backup_id: str,
    db: Session = Depends(get_db)
):
    """Restore from backup."""
    try:
        # Stop accepting new requests
        # (implementation depends on deployment)

        success = restore_coordinated_backup(db, backup_id)

        if success:
            logger.info(f"Restored backup: {backup_id}")
            return {"status": "success", "backup_id": backup_id}
        else:
            raise HTTPException(status_code=500, detail="Restore failed")
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

## Automated Backups

### Cron Job Setup

```bash
# crontab -e

# Daily backup at 2 AM
0 2 * * * cd /path/to/agents_memory && curl -X POST -H "X-API-Key: $API_KEY" http://localhost:8000/api/admin/backup

# Weekly cleanup of old backups (Sundays at 3 AM)
0 3 * * 0 cd /path/to/agents_memory && python scripts/cleanup_backups.py
```

### Python Script for Cleanup

```python
# scripts/cleanup_backups.py

import os
from app.services.backup_service import delete_old_sqlite_backups, delete_old_qdrant_snapshots
from dotenv import load_dotenv

load_dotenv()

RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", 30))

if __name__ == "__main__":
    # Delete old SQLite backups
    sqlite_deleted = delete_old_sqlite_backups(RETENTION_DAYS)
    print(f"Deleted {sqlite_deleted} old SQLite backups")

    # Delete old Qdrant snapshots
    qdrant_deleted = delete_old_qdrant_snapshots(RETENTION_DAYS)
    print(f"Deleted {qdrant_deleted} old Qdrant snapshots")

    print(f"Cleanup complete. Retention: {RETENTION_DAYS} days")
```

## Backup Verification

### Integrity Check

```python
# scripts/verify_backup.py

import sqlite3
import os

def verify_sqlite_backup(backup_path: str) -> bool:
    """Verify SQLite backup integrity."""
    try:
        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()

        # Run integrity check
        cursor.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()

        conn.close()

        return result[0] == "ok"
    except Exception as e:
        print(f"Verification failed: {e}")
        return False

def verify_qdrant_snapshot(snapshot_name: str) -> bool:
    """Verify Qdrant snapshot."""
    try:
        # Try to load snapshot info
        snapshot_info = client.get_snapshot_info(
            collection_name=QDRANT_COLLECTION,
            snapshot_name=snapshot_name
        )

        return snapshot_info is not None
    except Exception as e:
        print(f"Verification failed: {e}")
        return False

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python verify_backup.py <backup_id>")
        sys.exit(1)

    backup_id = sys.argv[1]
    sqlite_path = f"./data/backups/{backup_id}.db"

    print(f"Verifying backup: {backup_id}")

    # Verify SQLite
    if verify_sqlite_backup(sqlite_path):
        print("✅ SQLite backup verified")
    else:
        print("❌ SQLite backup corrupted")
        sys.exit(1)

    # Note: Qdrant snapshot verification requires snapshot name
    # (implementation depends on your metadata tracking)

    print("✅ Backup verification complete")
```

## Disaster Recovery Plan

### Scenario 1: Database Corruption

**Symptoms**: SQLite queries fail, database locked

**Steps**:
1. Stop application
2. Restore from latest backup
3. Start application
4. Verify data integrity
5. Investigate cause

### Scenario 2: Vector Store Corruption

**Symptoms**: Search returns no results or incorrect results

**Steps**:
1. Verify Qdrant collection health
2. If corrupted, restore from snapshot
3. If snapshots unavailable, trigger re-embed:
   ```bash
   POST /api/admin/reembed
   {
     "confirm": "I understand this will delete and regenerate all embeddings"
   }
   ```

### Scenario 3: Complete Data Loss

**Symptoms**: Both databases corrupted or lost

**Steps**:
1. Check for remote backups (if configured)
2. Check for user's markdown exports
3. Restore from most recent source
4. Implement offsite backup going forward

### Scenario 4: Inconsistent State

**Symptoms**: Notes in SQLite but not in Qdrant (or vice versa)

**Steps**:
1. Identify unsynced notes:
   ```sql
   SELECT * FROM notes WHERE synced = FALSE;
   ```
2. Trigger sync job:
   ```bash
   POST /api/admin/sync-embeddings
   ```
3. For orphaned Qdrant vectors (no SQLite note):
   - Manually delete or recreate notes
   - Or accept as data loss

## Offsite Backup

### S3 Integration (Optional)

```python
# app/services/backup_service.py

import boto3

S3_BUCKET = os.getenv("BACKUP_S3_BUCKET")
S3_PREFIX = os.getenv("BACKUP_S3_PREFIX", "backups")

def upload_to_s3(local_path: str, s3_key: str) -> bool:
    """Upload backup to S3."""
    try:
        s3 = boto3.client('s3')
        s3.upload_file(local_path, S3_BUCKET, s3_key)
        return True
    except Exception as e:
        print(f"S3 upload failed: {e}")
        return False

def download_from_s3(s3_key: str, local_path: str) -> bool:
    """Download backup from S3."""
    try:
        s3 = boto3.client('s3')
        s3.download_file(S3_BUCKET, s3_key, local_path)
        return True
    except Exception as e:
        print(f"S3 download failed: {e}")
        return False
```

## Configuration

Add to `.env`:

```bash
# Backup Configuration
BACKUP_DIR=./data/backups
BACKUP_RETENTION_DAYS=30
BACKUP_AUTO_ENABLED=true
BACKUP_SCHEDULE="0 2 * * *"  # Cron schedule (2 AM daily)

# Offsite Backup (optional)
BACKUP_S3_BUCKET=
BACKUP_S3_PREFIX=agents_memory/backups
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
```

## Monitoring

### Backup Alerts

Set up monitoring for:
1. Backup failures
2. Backup age (last successful backup > 24 hours)
3. Backup storage size
4. Restore test failures

Example using simple logging:

```python
# app/services/backup_service.py

def check_backup_health():
    """Check backup health and alert if needed."""
    backups = list_backups()

    if not backups:
        logger.error("No backups found!")
        # Send alert (email, Slack, etc.)
        return False

    latest = backups[0]
    backup_time = datetime.fromisoformat(latest["created_at"])
    age = datetime.now() - backup_time

    if age > timedelta(hours=24):
        logger.warning(f"Latest backup is {age} old")
        # Send alert
        return False

    logger.info(f"Backup health OK (latest: {age} old)")
    return True
```

## Best Practices

1. **Test Restores Regularly**: Don't assume backups work until you've tested restoration
2. **Offsite Backups**: Keep at least one copy offsite (S3, rsync to another server)
3. **Encrypt Sensitive Data**: If backups contain sensitive info, encrypt them
4. **Document Recovery Steps**: Keep this document up to date
5. **Monitor Backup Jobs**: Set up alerts for backup failures
6. **Automate Everything**: Manual backups get forgotten
7. **Version Control Backups**: Keep track of schema changes vs backup compatibility

## Next Steps

1. ✅ Implement backup service
2. ✅ Add API endpoints
3. ✅ Set up automated backups
4. 📋 Add offsite backup (S3)
5. 📋 Implement incremental backups
6. 📋 Set up monitoring and alerts
7. 📋 Document recovery runbooks
8. 📋 Test disaster recovery scenarios
