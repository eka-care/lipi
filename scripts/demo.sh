#!/usr/bin/env bash
# Walks the phase 1 flow against a running server (`make dev`). Grows with each build step.
set -euo pipefail

BASE="${LIPI_BASE_URL:-http://localhost:8100}"

echo "== discovery"
curl -sf "$BASE/.well-known/scribe-exchange" | python3 -m json.tool
