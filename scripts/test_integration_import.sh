#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PROJECT="${IMPORT_E2E_PROJECT:-zk-memory-import-e2e-local-$$}"
COMPOSE=(docker compose -p "$PROJECT" -f docker-compose.test.import.yml)
LOG_FILE="${IMPORT_E2E_LOG_FILE:-import-e2e-compose.log}"

cleanup() {
  "${COMPOSE[@]}" logs --timestamps --no-color >"$LOG_FILE" 2>/dev/null || true
  "${COMPOSE[@]}" down -v >/dev/null 2>&1 || true
}
trap cleanup EXIT
trap 'exit 130' INT TERM

if [[ -x .venv/bin/python ]]; then
  PYTHON=.venv/bin/python
else
  PYTHON=python3
fi

(
  cd cli
  go build -o dist/memory .
)

"${COMPOSE[@]}" up -d --build
PORT="$("${COMPOSE[@]}" port agents-memory-test-import 8000 | awk -F: 'NR == 1 { print $NF }')"
if [[ -z "$PORT" ]]; then
  echo "unable to determine import E2E API port" >&2
  exit 1
fi

E2E_IMPORT_TESTS=1 \
IMPORT_API_URL="http://127.0.0.1:$PORT" \
CLI_BIN=cli/dist/memory \
"$PYTHON" -m pytest tests/e2e/test_import_workflow.py -v
