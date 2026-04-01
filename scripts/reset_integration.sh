#!/usr/bin/env bash
# reset_integration.sh — wipe all integration test data for a clean re-run
#
# Usage:
#   ./scripts/reset_integration.sh
#
# What it does:
#   1. Deletes data/integration.db (SQLite)
#   2. Drops the test_memory Qdrant collection
#
# Qdrant must be running (docker compose up qdrant).

set -euo pipefail

QDRANT_HOST="${QDRANT_HOST:-localhost}"
QDRANT_PORT="${QDRANT_PORT:-6333}"
COLLECTION="test_memory"
DB_PATH="data/integration.db"

echo "==> Resetting integration test environment"

# 1. SQLite
if [ -f "$DB_PATH" ]; then
  rm -f "$DB_PATH"
  echo "    Deleted $DB_PATH"
else
  echo "    $DB_PATH not found, skipping"
fi

# 2. Qdrant collection
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -X DELETE "http://${QDRANT_HOST}:${QDRANT_PORT}/collections/${COLLECTION}")

case "$HTTP_STATUS" in
  200) echo "    Dropped Qdrant collection '${COLLECTION}'" ;;
  404) echo "    Qdrant collection '${COLLECTION}' not found, skipping" ;;
  *)   echo "    WARNING: unexpected HTTP status ${HTTP_STATUS} from Qdrant" ;;
esac

echo "==> Done. Run tests with:"
echo "    INTEGRATION_TESTS=1 uv run pytest tests/integration/ -v"
