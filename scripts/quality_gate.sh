#!/usr/bin/env bash
# The single quality-gate entry point used locally and by CI.
#
# P0 intentionally leaves agent:core_eval red. Every stage still runs so an
# empty or early-failing stage cannot conceal later failures.

set -uo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if [[ -x .venv/bin/python ]]; then
  python_cmd=(.venv/bin/python)
  ruff_cmd=(.venv/bin/ruff)
  mypy_cmd=(.venv/bin/mypy)
  pytest_cmd=(.venv/bin/pytest)
else
  python_cmd=(python)
  ruff_cmd=(ruff)
  mypy_cmd=(mypy)
  pytest_cmd=(pytest)
fi

stage_count=0
failed_stages=()

run_stage() {
  local name="$1"
  shift
  stage_count=$((stage_count + 1))
  printf '\n[%02d/15] %s\n' "$stage_count" "$name"
  if "$@"; then
    printf 'PASS %s\n' "$name"
  else
    local status=$?
    failed_stages+=("$name ($status)")
    printf 'FAIL %s (exit %d)\n' "$name" "$status"
  fi
}

secret_scan() {
  local matches
  matches="$(rg --hidden \
    --glob '!.git/**' \
    --glob '!.venv/**' \
    --glob '!node_modules/**' \
    --glob '!frontend/node_modules/**' \
    --glob '!.env' \
    --glob '!.env.*' \
    --glob '!package-lock.json' \
    --glob '!frontend/package-lock.json' \
    --line-number 'sk-[A-Za-z0-9_-]{20,}' . || true)"
  if [[ -n "$matches" ]]; then
    printf '%s\n' 'credential-shaped text found (file names and lines withheld)'
    return 1
  fi
  return 0
}

core_eval_placeholder() {
  printf '%s\n' 'agent core_eval is not implemented until P3 (intentional P0 failure)'
  return 1
}

run_stage 'backend:format' "${ruff_cmd[@]}" format --check backend
run_stage 'backend:lint' "${ruff_cmd[@]}" check backend
run_stage 'backend:typecheck' "${mypy_cmd[@]}" backend/app
run_stage 'backend:tests' "${pytest_cmd[@]}" backend/tests -m 'not spike and not live'

run_stage 'frontend:format' npm run frontend:format
run_stage 'frontend:lint' npm run frontend:lint
run_stage 'frontend:typecheck' npm run frontend:typecheck
run_stage 'frontend:tests' npm run frontend:test

run_stage 'agent:schema_validation' "${pytest_cmd[@]}" \
  backend/tests/spike/test_quality_gate_smoke.py -k schema_validation
run_stage 'agent:bounded_loop_check' "${pytest_cmd[@]}" \
  backend/tests/spike/test_quality_gate_smoke.py -k bounded_loop
run_stage 'agent:core_eval' core_eval_placeholder

run_stage 'architecture:forbidden_import_check' "${pytest_cmd[@]}" \
  backend/tests/test_architecture.py -k 'framework or outer_layer or checker'
run_stage 'architecture:dependency_cycle_check' "${pytest_cmd[@]}" \
  backend/tests/test_architecture.py -k cycle
run_stage 'security:secret_scan' secret_scan
run_stage 'journey:end_to_end_core_flow' npm run journey:smoke

printf '\nQuality gate: %d/15 stages executed.\n' "$stage_count"
if ((${#failed_stages[@]})); then
  printf 'Failed stages:\n'
  printf '  - %s\n' "${failed_stages[@]}"
  exit 1
fi
printf '%s\n' 'All stages passed.'
