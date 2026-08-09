#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

ruff_bin="ruff"
mypy_bin="mypy"
pytest_bin="pytest"
if [[ -x "$repo_root/.venv/bin/ruff" ]]; then ruff_bin="$repo_root/.venv/bin/ruff"; fi
if [[ -x "$repo_root/.venv/bin/mypy" ]]; then mypy_bin="$repo_root/.venv/bin/mypy"; fi
if [[ -x "$repo_root/.venv/bin/pytest" ]]; then pytest_bin="$repo_root/.venv/bin/pytest"; fi

"$ruff_bin" format --check backend migrations
"$ruff_bin" check backend migrations
"$mypy_bin" backend/app
"$pytest_bin" backend/tests

npm --prefix frontend run format:check
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend test
npm --prefix frontend run build
