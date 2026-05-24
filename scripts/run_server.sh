#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

APP_PATTERN='uvicorn server.main:app --host 0.0.0.0 --port 7171'

if pgrep -f "$APP_PATTERN" >/dev/null 2>&1; then
  echo "Stopping existing Freetopify server process(es)..."
  pkill -TERM -f "$APP_PATTERN"

  for _ in {1..30}; do
    if ! pgrep -f "$APP_PATTERN" >/dev/null 2>&1; then
      break
    fi
    sleep 0.2
  done

  if pgrep -f "$APP_PATTERN" >/dev/null 2>&1; then
    echo "Force-stopping stubborn server process(es)..."
    pkill -KILL -f "$APP_PATTERN"
  fi
fi

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

UVICORN_CMD=("/home/flex/Projects/freetopify/venv/bin/uvicorn" "server.main:app" "--host" "0.0.0.0" "--port" "7171")

if [ -n "${MAX_CONNECTIONS:-}" ] && [ "$MAX_CONNECTIONS" -gt 0 ]; then
  UVICORN_CMD+=("--limit-concurrency" "$MAX_CONNECTIONS")
fi

exec "${UVICORN_CMD[@]}"