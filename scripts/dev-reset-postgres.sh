#!/usr/bin/env bash
# dev-reset-postgres.sh — Wipe and recreate the PostgreSQL schema for dev use.
#
# Drops all tables in the running PostgreSQL container and re-applies Alembic
# migrations from scratch. Also clears the Qdrant collection so vector data
# stays in sync with the empty database.
#
# Usage:
#   ./scripts/dev-reset-postgres.sh                   # production compose (docker-compose.postgres.yml)
#   ./scripts/dev-reset-postgres.sh test              # test compose (docker-compose.test.postgres.yml)
#
# Requires the target compose stack to already be running.

set -euo pipefail

MODE="${1:-prod}"

if [[ "$MODE" == "test" ]]; then
    COMPOSE_FILE="docker-compose.test.postgres.yml"
    PG_SERVICE="postgres-test"
    APP_SERVICE="agents-memory-test-postgres"
    PG_DB="memory_test"
    QDRANT_PORT="6335"
    QDRANT_COLLECTION="test_memory_pg"
else
    COMPOSE_FILE="docker-compose.postgres.yml"
    PG_SERVICE="postgres"
    APP_SERVICE="agents-memory"
    PG_DB="memory"
    QDRANT_PORT="6333"
    QDRANT_COLLECTION="notes_embeddings"
fi

echo "==> Resetting PostgreSQL (${COMPOSE_FILE} / db: ${PG_DB})"

# 1. Drop and recreate the public schema (fastest full wipe)
docker compose -f "$COMPOSE_FILE" exec -T "$PG_SERVICE" \
    psql -U memory -d "$PG_DB" <<'SQL'
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO memory;
SQL

echo "    Schema dropped and recreated."

# 2. Re-apply Alembic migrations inside the running app container
docker compose -f "$COMPOSE_FILE" exec -T "$APP_SERVICE" \
    sh -c "PYTHONPATH=src python -m alembic upgrade head"

echo "    Alembic migrations applied."

# 3. Delete the Qdrant collection so it gets recreated fresh on next request
curl -s -o /dev/null -w "    Qdrant collection delete: HTTP %{http_code}\n" \
    -X DELETE "http://localhost:${QDRANT_PORT}/collections/${QDRANT_COLLECTION}"

echo "==> Done. Database is empty and ready."
