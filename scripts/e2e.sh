#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
E2E_TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/foodflow-e2e.XXXXXX")"
BACKEND_LOG="$E2E_TEMP_DIR/backend.log"
FRONTEND_LOG="$E2E_TEMP_DIR/frontend.log"
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if [[ -n "$FRONTEND_PID" ]]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  if [[ -n "$BACKEND_PID" ]]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  wait "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" 2>/dev/null || true
  if [[ $exit_code -ne 0 ]]; then
    echo "E2E failed. Backend log:"
    tail -n 80 "$BACKEND_LOG" 2>/dev/null || true
    echo "E2E failed. Frontend log:"
    tail -n 80 "$FRONTEND_LOG" 2>/dev/null || true
  fi
  rm -rf "$E2E_TEMP_DIR"
  exit "$exit_code"
}
trap cleanup EXIT INT TERM

wait_for_url() {
  local name=$1
  local url=$2
  local log_file=$3
  for _ in {1..120}; do
    if curl --fail --silent --show-error "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
  done
  echo "$name did not become ready at $url"
  tail -n 80 "$log_file" 2>/dev/null || true
  return 1
}

cd "$PROJECT_DIR"
export DATABASE_URL="sqlite:///$E2E_TEMP_DIR/foodflow-e2e.db"
export DEMO_MODE=true
export AGENT_TRANSPORT=replay
export DEEPSEEK_API_KEY=""
export DEEPSEEK_BASE_URL="https://provider.invalid/v1"
export DEEPSEEK_MODEL="deepseek-v4-flash"
export NEXT_PUBLIC_API_BASE_URL="http://localhost:8000"
export PLAYWRIGHT_BASE_URL="http://localhost:3000"

npm run data:migrate

npm run dev:backend >"$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
npm run dev:frontend >"$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

wait_for_url "FastAPI" "http://localhost:8000/health" "$BACKEND_LOG"
wait_for_url "Next.js" "http://localhost:3000" "$FRONTEND_LOG"

npm exec playwright test journey.spec.ts
