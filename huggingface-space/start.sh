#!/usr/bin/env bash
set -euo pipefail

ROOT="${HOME}/app"
cd "${ROOT}"
export PYTHONPATH="${ROOT}:${ROOT}/backend"
export HVAC_API_ORIGIN="${HVAC_API_ORIGIN:-http://127.0.0.1:8000}"

mkdir -p "${ROOT}/database"

uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!

for _ in $(seq 1 90); do
  if curl -sf http://127.0.0.1:8000/healthz >/dev/null 2>&1; then
    break
  fi
  if ! kill -0 "${API_PID}" 2>/dev/null; then
    echo "API process exited before becoming healthy."
    wait "${API_PID}" || true
    exit 1
  fi
  sleep 1
done

if ! curl -sf http://127.0.0.1:8000/healthz >/dev/null 2>&1; then
  echo "API did not become healthy in time."
  exit 1
fi

cd "${ROOT}/frontend"
exec npx --yes next start --hostname 0.0.0.0 --port "${PORT:-7860}"
