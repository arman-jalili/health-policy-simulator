#!/usr/bin/env bash
# Full demo walkthrough against a fresh, migrated database.
#
# Usage: DATABASE_URL=... make demo-walkthrough
# Requires: a local PostgreSQL reachable at DATABASE_URL, .venv installed.
set -euo pipefail
cd "$(dirname "$0")/.."

export ENV="${ENV:-local}"
export AUTH_MODE="${AUTH_MODE:-demo}"
export PERSISTENCE="${PERSISTENCE:-postgres}"
export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://hps:hps@localhost:5433/health_policy}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"
PORT="${DEMO_PORT:-8010}"
BASE="http://127.0.0.1:${PORT}"
LOG="${TMPDIR:-/tmp}/hps-demo-api.log"

alembic upgrade head
SEED_JSON="${TMPDIR:-/tmp}/hps-demo-seed.json"
.venv/bin/python -m shared.demo_seed >"$SEED_JSON"

.venv/bin/python -m uvicorn shared.app:create_app --factory \
  --host 127.0.0.1 --port "$PORT" >"$LOG" 2>&1 &
API_PID=$!
cleanup() {
  kill "$API_PID" >/dev/null 2>&1 || true
  wait "$API_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

for _ in $(seq 1 60); do
  if curl -fsS "$BASE/healthz" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done
if ! curl -fsS "$BASE/healthz" >/dev/null 2>&1; then
  echo "API did not become healthy; log follows" >&2
  cat "$LOG" >&2
  exit 1
fi

PACK_ID=$(.venv/bin/python -c \
  'import json,sys; print(json.load(open(sys.argv[1]))["pack_ids"]["kassenstellen"])' \
  "$SEED_JSON")

.venv/bin/python -m shared.demo_walkthrough "$BASE" "$PACK_ID"
