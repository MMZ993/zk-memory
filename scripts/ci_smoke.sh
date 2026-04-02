#!/usr/bin/env bash
set -euo pipefail

API_URL="${MEMORY_API_URL:-http://localhost:8002}"
CLI_BIN="${CLI_BIN:-./cli/dist/memory}"

if [ ! -x "$CLI_BIN" ]; then
  exit 1
fi

create_note() {
  "$CLI_BIN" notes create --title "$1" --content "$2" --tags "$3"
}

extract_id() {
  python -c 'import json,sys; print(json.loads(sys.stdin.read())["id"])'
}

MEMORY_API_URL="$API_URL" "$CLI_BIN" admin health --pretty >/dev/null

NOTE_A_JSON="$(MEMORY_API_URL="$API_URL" create_note "CI Smoke Note A" "CI smoke semantic anchor for hybrid search" "ci,smoke")"
NOTE_B_JSON="$(MEMORY_API_URL="$API_URL" create_note "CI Smoke Note B" "CI smoke follow-up linked context" "ci,smoke")"

NOTE_A_ID="$(printf '%s' "$NOTE_A_JSON" | extract_id)"
NOTE_B_ID="$(printf '%s' "$NOTE_B_JSON" | extract_id)"

SEARCH_JSON="$(MEMORY_API_URL="$API_URL" "$CLI_BIN" notes search "semantic anchor" --mode hybrid --pretty)"
printf '%s' "$SEARCH_JSON" | python -c 'import json,sys; data=json.loads(sys.stdin.read()); ids=[x.get("id") for x in data.get("results",[])]; raise SystemExit(0 if len(ids) > 0 else 1)'

MEMORY_API_URL="$API_URL" "$CLI_BIN" notes links link --source "$NOTE_A_ID" --target "$NOTE_B_ID" --relation-type related_to >/dev/null

GRAPH_JSON="$(MEMORY_API_URL="$API_URL" "$CLI_BIN" notes links graph "$NOTE_A_ID" --depth 1 --pretty)"
printf '%s' "$GRAPH_JSON" | python -c 'import json,sys; data=json.loads(sys.stdin.read()); results=data.get("results",[]); ids=[x.get("id") for x in results]; raise SystemExit(0 if len(ids) > 0 else 1)'

MEMORY_API_URL="$API_URL" "$CLI_BIN" notes delete "$NOTE_A_ID" >/dev/null
MEMORY_API_URL="$API_URL" "$CLI_BIN" notes delete "$NOTE_B_ID" >/dev/null
