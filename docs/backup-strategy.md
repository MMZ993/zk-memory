# Backup Strategy

Backups are external to the API. Back up the SQL database and Qdrant data at the
same point in time, then verify that both artifacts can be restored.

## SQLite deployments

The default database is `data/memory.db`. Stop the application before copying it,
or use SQLite's online backup command while it is running.

```bash
mkdir -p data/backups
sqlite3 data/memory.db ".backup data/backups/memory_$(date +%Y%m%d_%H%M%S).db"
```

To restore, stop the application, replace `data/memory.db` with the backup, then
start the application again.

## PostgreSQL deployments

The deployment compose stores PostgreSQL data at `POSTGRES_DATA_DIR`. Prefer a
logical dump for routine backups:

```bash
mkdir -p backups

docker compose --env-file .env.deploy -f docker-compose.deploy.yml \
  exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
  > "backups/postgres_$(date +%Y%m%d_%H%M%S).sql"
```

Restore only while the application is stopped and after selecting the intended
backup. Use `psql` or the deployment platform's documented restore procedure;
restoring a database overwrites current data.

## Qdrant

Qdrant data is stored at `QDRANT_DATA_DIR` in the deployment compose or
`qdrant_storage/` in the local compose stack. Either stop Qdrant and copy that
directory, or create a native snapshot:

```bash
curl -X POST http://localhost:6333/collections/notes_embeddings/snapshots
```

Use Qdrant's snapshot recovery endpoint or replace the storage directory while
Qdrant is stopped to restore it.

## Consistency and recovery

A restored SQL database can contain notes whose vectors are pending or failed.
The note sync state records the status, attempt count, last error, and timestamps.
After restoring both stores, run the embedding repair operation if required:

```bash
curl -X POST -H "X-API-Key: $MEMORY_API_KEY" \
  http://localhost:8000/api/admin/sync-embeddings
```

The supplied key must have the `admin` scope. See [API access scopes](api-scopes.md).

For production deployments, make a pre-deploy backup and retain backups according
to the policy documented in [the UAT/PROD rollout runbook](uat-prod-rollout.md).
