#!/usr/bin/env bash
# Container entrypoint: migrate, optionally seed, then serve.
#
# Migrations run here (not in compose) so the API never starts against an unmigrated schema, and so a
# `docker compose run --rm backend` command inherits the same guarantee.
#
# HPS_SEED_ON_BOOT=1 runs the idempotent demo seed once before serving; leave it 0 for a corpus you
# ingest yourself, and call `python -m shared.demo_seed` explicitly instead.
set -euo pipefail

port="${API_PORT:-8000}"

echo "[entrypoint] alembic upgrade head"
alembic upgrade head

if [[ "${HPS_SEED_ON_BOOT:-0}" == "1" ]]; then
  echo "[entrypoint] seeding the demo corpus (idempotent)"
  python -m shared.demo_seed > "/tmp/demo-seed.json" || {
    echo "[entrypoint] demo seed failed; continuing without it (see the log above)" >&2
  }
  if [[ -s /tmp/demo-seed.json ]]; then
    cat /tmp/demo-seed.json
  fi
fi

echo "[entrypoint] starting uvicorn on 0.0.0.0:${port}"
# No --proxy-headers: uvicorn would trust a spoofable X-Forwarded-For from any client and replace
# request.client.host with it, which would defeat the demo-mode host guard (AUTH_DEMO_TRUSTED_CIDRS).
# The frontend proxy forwards a fixed header list and never sets X-Forwarded-For, so the peer address
# is the trustworthy one.
exec python -m uvicorn shared.app:create_app --factory \
  --host "${API_HOST:-0.0.0.0}" \
  --port "${port}"
