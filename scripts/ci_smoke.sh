#!/usr/bin/env bash
set -euo pipefail

trap 'echo "ci_smoke.sh failed at line $LINENO" >&2' ERR

API_URL="${MEMORY_API_URL:-http://localhost:8002}"
CLI_BIN="${CLI_BIN:-./cli/dist/memory}"

if [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  PYTHON_BIN="python"
fi

if [ ! -x "$CLI_BIN" ]; then
  exit 1
fi

create_note() {
  "$CLI_BIN" notes create --title "$1" --content "$2" --tags "$3"
}

extract_id() {
  "$PYTHON_BIN" -c 'import json,sys; print(json.loads(sys.stdin.read())["id"])'
}

wait_for_hybrid_result() {
  local query="$1"
  local attempts=10
  local sleep_seconds=2
  local i
  for ((i=1; i<=attempts; i++)); do
    local result
    result="$(MEMORY_API_URL="$API_URL" "$CLI_BIN" notes search "$query" --mode hybrid --pretty)"
    if printf '%s' "$result" | "$PYTHON_BIN" -c 'import json,sys; data=json.loads(sys.stdin.read()); raise SystemExit(0 if data.get("results") else 1)'; then
      printf '%s' "$result"
      return 0
    fi
    sleep "$sleep_seconds"
  done
  echo "hybrid search did not return results for query: $query" >&2
  return 1
}

wait_for_graph_result() {
  local note_id="$1"
  local attempts=10
  local sleep_seconds=1
  local i
  for ((i=1; i<=attempts; i++)); do
    local result
    result="$(MEMORY_API_URL="$API_URL" "$CLI_BIN" notes links graph "$note_id" --depth 1 --pretty)"
    if printf '%s' "$result" | "$PYTHON_BIN" -c 'import json,sys; data=json.loads(sys.stdin.read()); raise SystemExit(0 if data.get("results") else 1)'; then
      printf '%s' "$result"
      return 0
    fi
    sleep "$sleep_seconds"
  done
  echo "graph query did not return results for note: $note_id" >&2
  return 1
}

delete_with_retry() {
  local note_id="$1"
  local attempts=5
  local sleep_seconds=1
  local i
  for ((i=1; i<=attempts; i++)); do
    if MEMORY_API_URL="$API_URL" "$CLI_BIN" notes delete "$note_id" >/dev/null; then
      return 0
    fi
    sleep "$sleep_seconds"
  done
  echo "failed to delete note after retries: $note_id" >&2
  return 1
}

wait_for_health() {
  local attempts=20
  local sleep_seconds=2
  local i
  for ((i=1; i<=attempts; i++)); do
    if MEMORY_API_URL="$API_URL" "$CLI_BIN" admin health --pretty >/dev/null; then
      return 0
    fi
    sleep "$sleep_seconds"
  done
  echo "health check did not pass for $API_URL" >&2
  return 1
}

wait_for_health

NOTE_A_JSON="$(MEMORY_API_URL="$API_URL" create_note "CI Smoke Note A" "CI smoke semantic anchor for hybrid search" "ci,smoke")"
NOTE_B_JSON="$(MEMORY_API_URL="$API_URL" create_note "CI Smoke Note B" "CI smoke follow-up linked context" "ci,smoke")"

NOTE_A_ID="$(printf '%s' "$NOTE_A_JSON" | extract_id)"
NOTE_B_ID="$(printf '%s' "$NOTE_B_JSON" | extract_id)"

SEARCH_JSON="$(wait_for_hybrid_result "semantic anchor")"

MEMORY_API_URL="$API_URL" "$CLI_BIN" notes links link --source "$NOTE_A_ID" --target "$NOTE_B_ID" --relation-type related_to >/dev/null

GRAPH_JSON="$(wait_for_graph_result "$NOTE_A_ID")"

delete_with_retry "$NOTE_A_ID"
delete_with_retry "$NOTE_B_ID"
