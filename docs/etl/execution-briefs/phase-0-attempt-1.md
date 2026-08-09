# Phase 0 execution brief — freeze minimal contracts

Project: KiwiHarvest FoodFlow
Phase: 0 — Freeze minimal contracts
Attempt: 1
Status: implementation snapshot for Sol review
As of: 2026-08-09 (Pacific/Auckland)

## Goal

Create the smallest strict source, evidence, origin, simulation-rule, bundle,
scenario, and control-plane contracts needed by later ETL phases. Checked-in
control files must parse, references must resolve, every simulated scalar field
emitted against the current `Base.metadata` must have exactly one rule owner,
raw payload boundaries must fail closed, and bundle integrity must be
deterministic and non-circular. Phase 0 has no network or database side effect.

## Current repository evidence

- The current working tree, including its uncommitted schema foundation, is the
  input. The base revision is `234981319170b43b209fea3371f460c44d3c39a8`.
- `backend.app.models.Base.metadata` currently exposes exactly 29 tables.
- `ImportBatch.idempotency_key` is replay identity; `external_batch_id` is an
  optional source-provided identity. `SourceRecord` has `raw_reference`, JSONB
  `raw_payload`, and optional direct source-record links exist on some domain
  tables.
- No ETL package, ETL tests, or ETL control files existed at the start of this
  attempt.
- Python 3.12.7, Pydantic 2.13.4, SQLAlchemy 2.0.51, pytest, ruff, and mypy
  are available in the existing project virtual environment.

## Isolation and setup

Implementation is performed only in the isolated snapshot under `/private/tmp`.
The original checkout is read-only for this attempt and must not receive any
Phase 0 writes or integration. The snapshot was copied from the current
working tree while excluding `.git`, `.venv`, `node_modules`, caches, generated
artifacts, and build directories. Verification uses:

`/Users/heminghan/Woolworth_food_waste/.venv/bin/{python,pytest,ruff,mypy}`

Only stdlib, Pydantic, SQLAlchemy metadata, pytest, ruff, and mypy may be used.
No dependency, network client, DB engine/session, Alembic command, Docker
command, or external process is part of this phase.

## Allowed write scope

The exact project files allowed to change are:

- `docs/etl/execution-briefs/phase-0-attempt-1.md`
- `backend/app/etl/__init__.py`
- `backend/app/etl/contracts.py`
- `backend/app/etl/manifest.py`
- `data/etl/manifests/sources.v1.json`
- `data/etl/evidence/evidence-register.v1.json`
- `data/etl/rules/simulation-rules.v1.json`
- `data/etl/reference/demo-scenario.v1.json`
- `backend/tests/etl/__init__.py`
- `backend/tests/etl/test_contracts.py`
- `backend/tests/etl/test_manifest.py`

Everything else is forbidden, including `docs/evidence-backed-etl-plan-xml.md`,
`README.md`, `pyproject.toml`, `uv.lock`, `package.json`, `.gitignore`,
`backend/app/models/**`, `migrations/**`, existing tests, and database data.
The master XML is not modified in this implementation pass.

## Data flow and contracts

Checked-in JSON control files flow through strict Pydantic models with extra
fields forbidden, unique-ID and cross-reference checks, metadata-derived exact
simulation coverage, deterministic control/content checksums, and an immutable
in-memory control-plane aggregate. There are no network or database writes.

The implementation provides:

1. A discriminated `data_origin` union for observed, derived,
   evidence-backed simulation, and unknown metadata. Variant-specific keys are
   strict and immutable.
2. Canonical entity references, ETL metadata, an exact raw payload envelope,
   deterministic serialized payload validation, recursive case-insensitive
   secret-key rejection, and a 65,536-byte serialized envelope ceiling. No
   truncation or silent redaction is allowed.
3. Strict versioned source and evidence manifests. Source boundaries include
   official Woolworths NZ Store Locator JSON, official MPI recalled-products
   HTML, reviewed KiwiHarvest branch JSON, reviewed recipient candidate CSV,
   and reviewed food-policy JSON. Dated count assertions are review
   expectations, not parser constants.
4. Strict versioned simulation rules with exact `table.column` coverage against
   current SQLAlchemy metadata, exactly-one rule ownership, and evidence
   reference resolution.
5. A versioned `realistic_demo` scenario policy containing only selectors,
   required cases, and pickup-then-receiving topology. It contains no generated
   values, coordinates, quantities, timestamps, mutable display names, or real
   pilot claims.
6. Deterministic canonical bundle content JSON, SHA-256 content checksum,
   fixed UUID5 bundle identity, and an envelope that rejects checksum mismatch.
7. Local-only loaders for the four control files and an immutable aggregate
   that includes deterministic file/content checksums. All loader failures
   include the relevant path or unresolved reference.

## Scenario policy boundaries

- The donor selector requires an AUK supermarket source key.
- The recipient selector requires current-public relationship evidence,
  non-protected identity, and a source-backed public coordinate. If no
  candidate later satisfies all conditions, Phase 3 must stop.
- Required cases are barcode and no-barcode, known and unknown capacity,
  success and negative matching branches, two human decision gates, and public
  versus scenario-operational location.
- Route topology is pickup followed by a receiving stop. It is not an
  optimization claim.
- Simulation rules preserve unknown route metrics without provider evidence,
  `not_checked` recall when no deterministic as-of match check exists,
  scenario-only `operator_confirmed` semantics, an independent donation
  quantity ceiling, and the known/unknown capacity distinction.

## Implementation order

1. Write this execution brief and preserve the exact allowed/forbidden scope.
2. Add focused tests and capture the expected failure while modules/control
   files are absent.
3. Implement strict contracts and local loaders.
4. Add the four versioned control files.
5. Run focused tests and make only the smallest corrections required.
6. Run formatting, lint, and type checks.
7. Verify that only allowed files differ from the isolated snapshot baseline.

## Sol correction 1

Sol review identified three contract defects and one governance typo. The
correction makes raw payload validation fail closed during envelope construction
across source payload and metadata, rejects duplicate canonical entity keys,
adds strict field-level provenance for mixed-origin canonical records, and
corrects the allowed-file count below. The focused tests and all required
verification commands must be rerun; this correction does not imply Sol
acceptance.

## Sol correction 2

Sol's second review found four remaining defects: missing origin/reference
semantics and duplicate normalized keys for canonical entity references,
simulation provenance values not being compared with actual fields, and
concrete values being allowed for unknown fields. The naive-datetime test also
needed valid field provenance so it asserted the intended timezone failure.
These boundaries and focused tests were corrected; the required pytest,
format, lint, mypy, smoke, and isolated-scope checks must be rerun. This
correction does not imply Sol acceptance.

## Acceptance criteria

- All eleven allowed files exist and no forbidden file changes.
- All four control files parse with strict validation and zero unresolved IDs.
- Every current simulated table scalar has exactly one rule owner; missing,
  duplicate, extra, and unknown-table cases fail.
- All four origin variants accept valid metadata and reject extra/mismatched
  keys.
- Nested secret-like raw payload keys and serialized payloads above 65,536
  bytes fail without truncation.
- Scenario config rejects extra generated-value keys.
- Bundle checksum and bundle ID are stable under mapping/record reordering,
  are non-circular, and change when content changes.
- Duplicate IDs and extra keys in control models fail.
- Dated source count assertions remain data, not parser constants.
- Tests make no network or database connection.

## Required verification commands

Run from the isolated snapshot:

```text
/Users/heminghan/Woolworth_food_waste/.venv/bin/pytest backend/tests/etl/test_contracts.py backend/tests/etl/test_manifest.py -q
/Users/heminghan/Woolworth_food_waste/.venv/bin/ruff format --check backend/app/etl backend/tests/etl
/Users/heminghan/Woolworth_food_waste/.venv/bin/ruff check backend/app/etl backend/tests/etl
/Users/heminghan/Woolworth_food_waste/.venv/bin/mypy backend/app/etl
```

Also run a short read-only Python command invoking
`load_control_plane(Path.cwd())` and printing source, evidence, rule, and target
counts. Expected result: all commands pass, no unresolved references, and zero
missing/extra/duplicate target paths.

## Out of scope and handoff

HTTP fetching/parsing, reviewed source-record creation, transforms, simulation
generation, CLI, PostgreSQL sessions, migrations, load/replay, README changes,
master-result append, production hardening, and all future-phase code are out
of scope.

Handoff must report the isolated path, exact files changed, implementation
summary, the pre-code test failure, every verification command/result, source /
evidence / rule / target counts, coverage result, remaining risks, and any
master-plan conflicts. Do not integrate this snapshot into the original
checkout and do not claim Phase 0 passed; Sol decides after review.
