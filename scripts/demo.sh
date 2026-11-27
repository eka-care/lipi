#!/usr/bin/env bash
# Walks the phase 1 flow against a running server (`make dev`). Grows with each build step.
set -euo pipefail

BASE="${LIPI_BASE_URL:-http://localhost:8100}"

echo "== discovery"
curl -sf "$BASE/.well-known/scribe-exchange" | python3 -m json.tool

echo "== create a session"
SESSION=$(curl -sf -X POST "$BASE/v1/sessions" -H 'Content-Type: application/json' \
  -d '{"metadata": {"visit_ref": "demo-1"}, "client_session_id": "demo-visit"}')
echo "$SESSION" | python3 -m json.tool
SESSION_ID=$(echo "$SESSION" | python3 -c 'import json, sys; print(json.load(sys.stdin)["id"])')

echo "== read it back"
curl -sf "$BASE/v1/sessions/$SESSION_ID" | python3 -m json.tool
