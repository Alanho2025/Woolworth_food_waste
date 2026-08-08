#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

docker compose up -d postgres

for attempt in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready \
    -U "${POSTGRES_USER:-foodflow}" \
    -d "${POSTGRES_DB:-foodflow}" >/dev/null 2>&1; then
    break
  fi

  if [[ "$attempt" == "30" ]]; then
    echo "PostgreSQL did not become ready within 30 seconds." >&2
    exit 1
  fi

  sleep 1
done

python_bin="python"
if [[ -x "$repo_root/.venv/bin/python" ]]; then
  python_bin="$repo_root/.venv/bin/python"
fi

exec "$python_bin" -m uvicorn backend.app.main:app \
  --reload \
  --port "${BACKEND_PORT:-8000}"
