# Phase 1 execution brief — bounded real-source snapshots and reviewed inputs

Project: KiwiHarvest FoodFlow  
Phase: 1 — bounded source snapshots and reviewed research inputs  
Attempt: 1  
Status: implementation in progress; isolated snapshot for Sol review  
As of: 2026-08-09 (Pacific/Auckland)  
Snapshot: `/private/tmp/kiwiharvest-phase1-attempt1.1wy3vF`  
Baseline: `/private/tmp/kiwiharvest-phase1-attempt1.1wy3vF.baseline.sha256`  

## Phase goal

Obtain safely bounded, immutable, source-linked snapshots for the explicit
Woolworths NZ store-locator source and the MPI recalled-products source through
the specified Jina Reader route, and commit only reviewed, versioned
KiwiHarvest branch, recipient-candidate, and broad food-policy inputs. The
output is reproducible and fail-closed, but is not route-ready operational
data and does not perform recall matching.

## Current repository evidence

- Phase 0 is present in `backend/app/etl/contracts.py` and
  `backend/app/etl/manifest.py`. Its Pydantic models reject extra contract
  fields and preserve the manifest `as_of` date and Pacific/Auckland timezone.
- `data/etl/manifests/sources.v1.json` is frozen as of 2026-08-09 and already
  describes two HTTP sources and three reviewed inputs. MPI is currently
  described as direct HTML; Phase 1 changes it to explicit `http_markdown`
  retrieval through Jina Reader while keeping its canonical authority URL.
- `data/etl/evidence/evidence-register.v1.json` registers the Woolworths,
  MPI, KiwiHarvest branch, recipient, and food-policy evidence. Phase 1 adds
  evidence for the Jina Reader route and MPI copyright/attribution boundary.
- `docs/research.md` records the 61 Auckland Woolworths supermarket rows, the
  54 FY25 recipient rows, the 9 current-public relationship rows, 3 identity
  overlaps, 60 distinct candidates, 58 source-backed approximate points, and
  the two unknown names `Hapori Tautua Collective` and `The Koha Shed - West
  Auckland`. It also records Highbrook and Rosedale public branch points and
  the broad accepted-food/safety boundaries.
- The Woolworths response shape is `Locator.storelist[*].storeDetail`; the
  sibling `tradingHours` object is ignored. Source postcodes such as `618`
  and `204` are emitted as four-digit strings `0618` and `0204`.
- The current dependency lock contains `httpx` 0.28.1 only through the dev
  extra. Phase 1 moves the existing `httpx>=0.27` requirement to runtime and
  changes only the root package dependency metadata in `uv.lock`.

## Isolation and setup

All project-file writes in this attempt are restricted to the snapshot named
above. The main checkout is never edited or integrated. The snapshot was copied
from the current working tree including dirty and untracked project files, but
excluding `.git`, `.venv`, caches, `node_modules`, and `data/etl/raw`. The
baseline file contains SHA-256 hashes for the 81 existing non-ignored project
files before this phase's first project write.

If the snapshot has no `.venv`, create and use only its own ignored environment:

```text
UV_CACHE_DIR=/private/tmp/kiwiharvest-phase1-uv-cache uv sync --locked --extra dev
```

No database engine/session, SQLAlchemy query, migration command, schema change,
DB write, crawler, geocoder, OCR, scheduler, auth flow, or network access is
used by the offline tests. Tests inject `httpx.MockTransport` or an injected
client and an injected clock.

## Allowed project write set

Only these files may change or be added in this isolated snapshot:

- `docs/etl/execution-briefs/phase-1-attempt-1.md`
- `backend/app/etl/contracts.py`
- `backend/app/etl/extract.py`
- `backend/app/etl/sources/__init__.py`
- `backend/app/etl/sources/woolworths.py`
- `backend/app/etl/sources/mpi_recalls.py`
- `data/etl/manifests/sources.v1.json`
- `data/etl/evidence/evidence-register.v1.json`
- `data/etl/reviewed/kiwiharvest-branches.v1.json`
- `data/etl/reviewed/recipient-candidates.v1.csv`
- `data/etl/reviewed/kiwiharvest-food-policy.v1.json`
- `backend/tests/etl/fixtures/woolworths-minimal.json`
- `backend/tests/etl/fixtures/mpi-recalls-minimal.md`
- `backend/tests/etl/test_extract.py`
- `backend/tests/etl/test_woolworths_source.py`
- `backend/tests/etl/test_mpi_recalls_source.py`
- `backend/tests/etl/test_reviewed_inputs.py`
- `backend/tests/etl/test_manifest.py`
- `.gitignore`
- `pyproject.toml`
- `uv.lock`

Everything else is forbidden. In particular, do not edit
`docs/evidence-backed-etl-plan-xml.md`, Phase 0 files not named above, model or
migration files, or any frontend file. Runtime files under `data/etl/raw/` are
ignored artifacts and are not part of the handoff write set.

## Affected components

- `SourceSpec` and `SourceManifest`: optional explicit `retrieval_url`, the
  concrete `http_markdown` source kind, and strict repository-relative/HTTPS
  boundaries.
- `backend.app.etl.extract`: bounded HTTP reading, exact-byte hashing,
  source selection for the two known HTTP source IDs, immutable raw/records/
  report artifacts, and the one-source CLI.
- `backend.app.etl.sources.woolworths`: pure `bytes -> allowlisted records +
  filter metadata` parsing for the `Locator.storelist` shape.
- `backend.app.etl.sources.mpi_recalls`: pure `bytes -> three-field records +
  year/count metadata` parsing for Jina Reader Markdown, with fail-closed WAF
  and canonical-source checks.
- Versioned manifest/evidence/reviewed files: explicit source boundaries and
  research-only truth labels.
- Focused ETL tests and fixtures: offline contract, determinism, immutable
  artifact, reviewed-input, and governance coverage.
- `pyproject.toml` and root lock metadata: move the already installed
  `httpx>=0.27` requirement from `dev` to runtime without other dependency
  changes.

## Data flow and order

1. Load and strictly validate `sources.v1.json`.
2. Select exactly one of `woolworths-store-locator` or
   `mpi-recalled-products`; no source registry or generic factory is added.
3. Resolve the canonical authority URL and, for MPI, the explicit Jina Reader
   retrieval URL.
4. Fetch with one `httpx.Client`, explicit timeout, redirect support, a 2xx
   requirement, declared-size precheck, and an actual streaming byte ceiling.
5. Validate response headers and body shape. Missing `Content-Type` is a
   visible Woolworths warning; an explicit incompatible MIME fails. MPI body
   challenge markers fail even when the status is 200.
6. Hash the exact response bytes and save/reuse an immutable raw file under
   `data/etl/raw/<as_of>/` with `.json` for Woolworths and `.md` for MPI.
7. Run the pure source parser on those exact bytes. Woolworths filters
   `storeDetail.state == "AUK"` then `division == "COUNTDOWN"`; MPI parses
   only Markdown list links inside the 2016..2026 year sections.
8. Apply manifest-dated expected counts and report drift without silently
   treating drift as success. Produce deterministic canonical records JSON and
   an immutable report JSON containing retrieval metadata, checksums, counts,
   warnings, drift, limitations, and attribution.
9. Reviewed research is stored separately as strict versioned branch JSON,
   recipient CSV, and food-policy JSON. These files are reference-only and
   never become route-ready or live operational state.
10. Print the concise report JSON from the CLI. No database or application
    loader is called.

## Implementation-level contracts

### SourceSpec extension

`SourceSpec.source_kind` accepts the existing HTTP/reviewed kinds plus
`http_markdown`. `retrieval_url: str | None` is optional. For HTTP sources,
both `url_or_path` (the canonical authority URL) and any `retrieval_url` must be
absolute HTTPS URLs. For reviewed sources, `url_or_path` must be a non-empty
repository-relative path with no absolute or parent-directory segment. The
canonical URL remains authoritative in reports even when retrieval uses Jina.

### Bounded fetch

`bounded_http_read` accepts a URL, max byte count, expected MIME, an explicit
timeout, and an optional injected client. It returns the exact body bytes, HTTP
status, observed content type, and warnings. It rejects transport/timeout
errors, non-2xx responses, invalid or over-limit `Content-Length`, incompatible
explicit MIME, and a streamed body that exceeds the limit. A missing MIME is
allowed only for the Woolworths source and is returned as a warning.

### Woolworths parser

`parse_woolworths_store_locator(payload: bytes, expected_count: int | None)`
requires valid JSON with `Locator.storelist`; each selected item reads only
`storeDetail` and ignores `tradingHours`. It counts input, AUK, and COUNTDOWN
filters; maps only store number, name, `addressLine1`, `addressLine2`, suburb,
four-digit postcode, state, country, latitude, longitude, and division; maps a
literal string `"null"` to JSON null; rejects missing identity, duplicates,
invalid coordinates, and out-of-range coordinates; and sorts by numeric store
number. It returns no manager, email, phone, facilities, hours, or other source
fields. An expected-count mismatch is recorded as drift for orchestration.

### MPI parser

`parse_mpi_recalled_products(payload: bytes, as_of: date,
expected_year_counts: Mapping[int, int] | None)` decodes strict UTF-8, rejects
Incapsula/challenge markers, requires the Jina Reader title, canonical `URL
Source`, reviewed-date marker, and exactly one section for every year 2016
through `as_of.year`. It extracts only list links inside those sections and
emits `year`, `title`, and `canonical_recall_url`. Recall URLs must prove the
canonical MPI recall path. Duplicate `(year, URL)` fails; the same URL in two
different years is allowed. It returns per-year counts and drift metadata.

### Immutable artifacts and report

For each source, the artifact set is raw bytes, canonical records JSON, and
report JSON beneath the dated raw directory. None may be silently overwritten.
An absent set is created using exclusive writes. An existing exact raw replay
must have a complete, coherent records/report pair whose checksums, paths,
source, date, and record contents agree; that set is reused without changing
its timestamp. A different raw body at the same path, or any partial/
incoherent set, fails before changing the old bytes. Runtime timestamps appear
only in the report. Canonical records and their checksum contain no retrieval
timestamp.

The report includes `source_id`, canonical URL, retrieval URL used, retrieval
method, manifest `as_of`/timezone, timezone-aware UTC `retrieved_at`, HTTP
status, observed content type or null, raw path/checksum/bytes, records
path/checksum/count, before/after/filter counts, warnings, drift, source
limitations, and MPI attribution where applicable. The MPI report identifies
the official MPI authority separately from Jina Reader retrieval and records
the CC BY 4.0 Crown-attribution boundary and third-party-material limitation.

### Reviewed truth boundary

- Branch JSON contains exactly the Highbrook and Rosedale public branch
  identities and research coordinates. Each coordinate is public/approximate,
  reference-only, non-operational as a point, not an entrance/loading bay,
  and not route-ready.
- Recipient CSV contains exactly 60 distinct organisation/site candidate
  identities: the 54 FY25 rows plus 6 non-overlapping current-public rows,
  while the three overlaps (Island Child, Kootuitui ki Papakura, and
  Māngere Budgeting Services Trust) retain separate FY25 and current-public
  evidence columns. It has exactly 58 coordinates and exactly two unknown
  names: Hapori Tautua Collective and The Koha Shed - West Auckland. Point
  classes are only A/I/S/H/U. It stores public source URLs, evidence periods,
  protected/sensitive status, current-status notes, and limitations. Every
  row is reference-only and `route_ready=false`; there is no capacity, need,
  receiving window, entrance, onboarding, or live-participation value.
- Food-policy JSON contains only broad ambient/fresh/frozen/prepared categories,
  documented handling boundaries, the chilled 5C rule, frozen-stays-frozen,
  rejection of recalled/opened/previously-served/spoiled food, and date-mark
  semantics. Site-specific capability, capacity, need, receiving window, and
  entrance remain explicitly unknown and are not materialised.
- Organisation names are public entity identities only. No personal identity,
  safe-house address, protected exact destination, or simulated operational
  value is added.

## State and rule ownership

The manifest owns source authority, retrieval URL, as-of date, byte/content
limits, and aggregate count assertions. The source adapters own only source
shape validation, filtering, field allowlists, normalization, and deterministic
record ordering. The extractor owns bounded transport, exact-byte hashing,
artifact immutability, report timestamps, and drift presentation. Reviewed
files own reviewed research facts and explicit unknowns; they do not promote
facts into live operational truth. Phase 1 owns no recall matching, recipient
matching, route selection, database persistence, or schema behavior.

## Acceptance criteria and mapped tests

- **AC-04 — bounded immutable real-source acquisition:**
  `test_extract.py` proves status/timeout/transport handling, declared and
  actual oversize rejection, explicit MIME rejection, Woolworths missing-MIME
  warning, create/replay/conflict/incomplete artifact behavior, raw/records/
  report checksums, and no overwrite.
- **AC-09 — explicit source/parser correctness:**
  `test_woolworths_source.py` proves exact nested shape, filters/counts,
  facility-order stability, null/postcode normalization, allowlist, duplicate/
  missing/coordinate failures. `test_mpi_recalls_source.py` proves reader
  markers, canonical source proof, required years, duplicate rules, WAF
  rejection, and three-field output.
- **AC-10 — deterministic canonical outputs:**
  source tests and extractor tests run identical semantic inputs in different
  mapping/list orders and compare raw/records checksums where ordering is
  irrelevant to source semantics.
- **AC-13 — reviewed KiwiHarvest inputs:**
  `test_reviewed_inputs.py` proves 2 branches, 60 unique candidates,
  58 coordinates/2 unknown, exact unknown names, relationship-period
  separation, point classes, protected constraints, source links, reference /
  route boundary, and absence of capacity/need/window fields.
- **AC-14 — governance and scope:**
  `test_manifest.py` checks manifest/retrieval boundaries, `test_extract.py`
  and reviewed tests check no DB/network use, the brief checks the Phase 1-only
  contract, and the final scope check compares the snapshot to the baseline and
  the allowed write set. The full Phase 0 ETL test set remains green.

## Required verification commands

Run from the isolated snapshot. If `.venv` is absent, first run the `uv sync`
command in the setup section with the task-specific cache path.

```text
UV_CACHE_DIR=/private/tmp/kiwiharvest-phase1-uv-cache uv lock
UV_CACHE_DIR=/private/tmp/kiwiharvest-phase1-uv-cache uv lock --check
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider backend/tests/etl/test_contracts.py backend/tests/etl/test_manifest.py backend/tests/etl/test_extract.py backend/tests/etl/test_woolworths_source.py backend/tests/etl/test_mpi_recalls_source.py backend/tests/etl/test_reviewed_inputs.py -q
.venv/bin/ruff format --check backend/app/etl backend/tests/etl
.venv/bin/ruff check backend/app/etl backend/tests/etl
.venv/bin/mypy --cache-dir=/private/tmp/kiwiharvest-phase1-mypy backend/app/etl
```

The brief records outcomes append-only after each required verification run.
At the time of writing, these commands are planned and have not yet been run
in this attempt.

After offline checks pass, the explicit CLI may be run once for each real
source. If the snapshot network is blocked, record that as an unavailable
live/provider verification; do not weaken tests or fabricate a report. Raw
runtime artifacts stay ignored and out of the handoff write set.

## Completion criteria

- Both concrete adapters and the explicit one-source CLI exist.
- Offline tests prove bounded, immutable, deterministic, fail-closed behavior
  without network or DB access, and all 37 Phase 0 tests remain passing.
- Reviewed files meet exact counts and preserve unknown/protected/current versus
  historical boundaries.
- Runtime `httpx` dependency and root lock metadata are coherent without
  unrelated upgrades.
- No guessed fact, simulated operational value, secret, personal identity,
  protected exact location, schema change, migration, DB write, generic
  crawler/framework, scheduler, auth, OCR, geocoding, recall matching, Phase 2
  transform, Phase 3 simulation, or loader is added.
- The handoff lists snapshot, baseline, every changed file, exact commands and
  outcomes, live results if attempted, and remaining risks.

## Risks, assumptions, decisions, and stop conditions

- Risk: public source bodies can drift after the reviewed 2026-08-09 evidence.
  Decision: fail on incompatible shape, duplicate identity, missing markers, or
  dated count drift; preserve exact bytes and report drift visibly.
- Risk: two raw Woolworths responses may differ only in irrelevant facility
  ordering. Decision: raw bytes remain distinct and immutable while allowlisted
  records remain deterministic; the same-as-of raw path never overwrites.
- Risk: MPI direct HTML is challenged by Imperva/Incapsula. Decision: Jina
  Reader is the explicit route, with canonical MPI authority retained
  separately and no silent fallback.
- Assumption: source decisions supplied with this brief are accepted evidence
  for this attempt; live HTTP behavior is reported only when actually observed.
- Assumption: the documented 3 overlaps are the three same-entity merges named
  above; the Women’s Refuge network current-public row remains separate from
  differently named FY25 organisation/site rows under the organisation-site
  boundary in `docs/research.md`.
- Stop immediately and report if `docs/research.md` cannot support the exact
  60-row merge/counts, a source term forbids this local artifact, a dependency
  beyond moving `httpx` is required, or any required fact would need guessing.

## Out of scope

Do not edit the master XML, create migrations/models, access PostgreSQL, add a
generic ETL framework, crawl or discover replacement sources, geocode, match
products to recalls, materialise recipient capacity/need/windows, create routes
or simulations, add authentication/scheduling/OCR, load data into the
application, commit/push/integrate, or implement Phase 2/3 behavior.

## Corrections (append-only)

None at initial writing.

## Verification outcomes (append-only)

- `python3 -m compileall -q backend/app/etl backend/tests/etl`: passed before
  the focused test run.
- `PYTHONDONTWRITEBYTECODE=1 /Users/heminghan/Woolworth_food_waste/.venv/bin/pytest -p no:cacheprovider backend/tests/etl/test_contracts.py backend/tests/etl/test_manifest.py backend/tests/etl/test_extract.py backend/tests/etl/test_woolworths_source.py backend/tests/etl/test_mpi_recalls_source.py backend/tests/etl/test_reviewed_inputs.py -q`: passed, 67 tests.
- `/Users/heminghan/Woolworth_food_waste/.venv/bin/ruff format --check backend/app/etl backend/tests/etl`: passed, 15 files already formatted.
- `/Users/heminghan/Woolworth_food_waste/.venv/bin/ruff check backend/app/etl backend/tests/etl`: passed.
- `/Users/heminghan/Woolworth_food_waste/.venv/bin/mypy --cache-dir=/private/tmp/kiwiharvest-phase1-mypy backend/app/etl`: passed, 7 source files checked.
- `UV_CACHE_DIR=/private/tmp/kiwiharvest-phase1-uv-cache uv lock --check`: passed, 45 packages resolved from the existing lock metadata.
- `UV_CACHE_DIR=/private/tmp/kiwiharvest-phase1-uv-cache uv lock`: attempted and blocked by sandbox DNS while fetching `https://pypi.org/simple/fastapi/`; the command did not modify `uv.lock`. The root lock metadata was then updated manually only for the existing `httpx` runtime move, and `uv lock --check` passed.
- `UV_CACHE_DIR=/private/tmp/kiwiharvest-phase1-uv-cache uv sync --locked --extra dev`: attempted in the snapshot, created its own ignored `.venv`, and then was blocked by DNS while fetching the already locked `ast-serialize==0.8.0` wheel. The main checkout environment was not modified. Verification therefore used the existing main-checkout `.venv` binaries read-only with the snapshot as cwd.
- The explicit CLI was attempted once per source after offline checks:
  `.../.venv/bin/python -m backend.app.etl.extract --source woolworths-store-locator --repo-root /private/tmp/kiwiharvest-phase1-attempt1.1wy3vF` and the equivalent MPI command. Both exited 1 with `HTTP transport failure: [Errno 8] nodename nor servname provided, or not known`; no live/provider report was fabricated.
- Reviewed-data read-only checks passed: JSON files parse; CSV has 60 rows, 54 FY25 names, 9 current-public names, 3 merged rows, 58 coordinate pairs, and exactly the two documented unknown names. The offline tests cover these checks.
- Baseline scope check passed: changed existing files are only
  `backend/app/etl/contracts.py`, `backend/tests/etl/test_manifest.py`,
  `data/etl/evidence/evidence-register.v1.json`,
  `data/etl/manifests/sources.v1.json`, `.gitignore`, `pyproject.toml`, and
  `uv.lock`; all new non-ignored files are within the allowed write set. The
  copied snapshot `.env` was removed before handoff; the main checkout `.env`
  was not modified.

## Corrections (append-only, after verification)

- The initial “planned and have not yet been run” note above was superseded by
  the verification outcomes recorded below it. The final offline result is 67
  passing tests, with live/provider extraction unavailable only because the
  sandbox could not resolve external hosts.
- The environment note is further clarified: the snapshot `.venv` used for the
  final exact commands is an ignored copy of the existing runtime environment,
  because the prescribed network-backed `uv sync` could not complete.

## Sol correction 1 — implementation plan (append-only)

This correction stays in `/private/tmp/kiwiharvest-phase1-attempt1.1wy3vF` and
uses only the correction write set supplied by Sol. The main checkout, the
master XML, and all other initial-handoff files remain out of scope.

### Confirmed correction evidence

- The captured Woolworths response is `Locator.storelist`; each item contains
  `storeDetail` and sibling `tradingHours`. The source identity field is
  `storeDetail.no`, while the source coordinate field is `longtitude`. The
  normalized output may retain `storeNumber` only as the explicit rename
  `no` → `storeNumber`. Postcodes are normalized to four-character strings.
- The captured MPI Reader Markdown uses exact level-two headings such as
  `## 2026 recalls` and ends with non-year level-two headings after the 2016
  section. The parser must stop at any next level-two heading, parse repeated
  identical `Last reviewed` values, and support optional quoted Markdown link
  titles without widening the three-field output.
- The initial implementation incorrectly allowed fixture-sized aggregate and
  per-year count drift to become a successful report, used visible direct
  exclusive writes, and conflated current relationship URLs with ordinary
  organisation/status/location evidence. These are implementation defects,
  not new source decisions.

### Correction data flow and ownership

1. Read the strict manifest and select one of the two known source IDs.
2. Fetch the manifest-selected retrieval URL with the existing bounded HTTP
   contract, then validate response shape/body markers before any artifact is
   created.
3. Hash and atomically publish exact raw bytes; parse them with the pure
   source adapter; fail on aggregate or dated per-year count drift before
   persistence.
4. Canonicalize allowlisted records, build a report containing
   `source_last_reviewed` (MPI date or Woolworths `null`), and atomically
   publish the coherent records/report set with immutable replay checks.
5. Keep reviewed branch and recipient files reference-only. Branch address
   evidence is separate from reviewed coordinate provenance. Recipient
   current relationship URLs are separate from general current status/location
   URLs; FY25 evidence remains historical and never upgrades itself to current.

### Correction implementation contracts

- `parse_woolworths_store_locator` reads `Locator.storelist[*].storeDetail.no`,
  ignores sibling `tradingHours`, filters `state == AUK` then
  `division == COUNTDOWN`, and emits the existing normalized `storeNumber`
  output key with four-digit postcodes and stable sorted records.
- `parse_mpi_recalled_products` recognizes only `## YYYY recalls`, bounds each
  section at the next level-two heading, parses only canonical list links,
  rejects duplicate links within a year, allows the same URL across years,
  and returns a parsed source review date. Extraction fails before artifact
  creation when aggregate or expected per-year counts differ.
- `_exclusive_write` uses a same-directory temporary file, flush/fsync, and an
  exclusive non-overwriting publish; its temporary name is removed on every
  path. Existing partial/coherence/conflict behavior remains fail-closed.
- Reviewed provenance is represented by explicit address/status/relationship
  and coordinate fields. No new geocoding, relationship, capacity, need,
  receiving-window, route, or operational fact is introduced.

### Correction tests and completion criteria

The mapped regression tests cover the real Woolworths key and rejection of the
invented `storeNumber` input, realistic MPI headings/link titles/footer
exclusion/review-date parsing, drift failure with zero artifacts, atomic temp
cleanup, immutable replay/conflict behavior, exact FY25/current-public name
sets, the 9-versus-51 relationship boundary, 58-versus-2 coordinate
provenance split, and the unchanged Phase 0 contract tests. Completion requires
all prescribed focused tests, ruff, mypy, lock, baseline/scope checks, and
pure real-snapshot smokes to pass; live CLI results are reported only if actual
reports are emitted.

### Correction stop conditions and non-goals

Stop and report if the existing research cannot support the exact names,
overlaps, coordinates, or source links, or if a dependency beyond moving the
existing `httpx` requirement is needed. Do not edit the master XML, initial
handoff files outside the correction set, database/schema/migrations, raw
handoff artifacts, or any later-phase matching, routing, simulation, or
operational capability.

## Sol correction 1 — verification outcomes (append-only)

The correction was completed in the existing isolated snapshot
`/private/tmp/kiwiharvest-phase1-attempt1.1wy3vF` only. The main checkout was
not written, the master XML was not edited, and no integration or commit was
performed.

### Correction files changed

Only these 13 files were changed relative to the initial handoff:

- `docs/etl/execution-briefs/phase-1-attempt-1.md`
- `backend/app/etl/extract.py`
- `backend/app/etl/sources/woolworths.py`
- `backend/app/etl/sources/mpi_recalls.py`
- `backend/tests/etl/fixtures/woolworths-minimal.json`
- `backend/tests/etl/fixtures/mpi-recalls-minimal.md`
- `backend/tests/etl/test_extract.py`
- `backend/tests/etl/test_woolworths_source.py`
- `backend/tests/etl/test_mpi_recalls_source.py`
- `backend/tests/etl/test_reviewed_inputs.py`
- `data/etl/reviewed/kiwiharvest-branches.v1.json`
- `data/etl/reviewed/recipient-candidates.v1.csv`
- `data/etl/evidence/evidence-register.v1.json`

The initial baseline at
`/private/tmp/kiwiharvest-phase1-attempt1.1wy3vF.baseline.sha256` still covers
81 existing non-ignored files. The final scope check found the same 7 modified
existing allowed files and 14 new allowed files as the initial handoff, with
no out-of-scope path, missing baseline file, or master XML change. Runtime raw
artifacts were absent after the live attempts and remain outside the handoff.

### Source and provenance outcomes

- Woolworths now reads the real `storeDetail.no` source key and documents the
  normalized `no` → `storeNumber` rename. The realistic fixture includes
  `facilityList`, `COUNTDOWN_LIQUOR`, `COUNTDOWN_PHARMACY`, and sibling
  `tradingHours`; a normalized `storeNumber` input is rejected. The parser
  preserves the exact raw source boundary, ignores trading hours/facilities,
  normalizes literal `null`, and emits four-digit postcodes.
- MPI now requires `## YYYY recalls`, stops at any next level-two heading,
  excludes footer/navigation bullets, supports extra bullet spacing and quoted
  link titles, and parses repeated identical reviewed dates. The real snapshot
  also exposed one official legacy recall URL path and one same-URL empty-link
  conversion artifact; the adapter accepts only the two observed official MPI
  recall path prefixes and requires the empty-link URL to repeat the primary
  URL. External URLs remain rejected.
- Aggregate and per-year count drift now raises an extraction error before raw,
  records, or report creation. Successful reports have `drift=[]`. Reports
  include `source_last_reviewed` (`2026-07-23` for MPI and `null` for
  Woolworths), and immutable existing-report checks compare that field.
- Artifact publication uses a same-directory temporary file, flush/fsync, an
  exclusive non-overwriting link publish, and cleanup of the temporary name.
  Replay, conflict, partial-set, and report-date coherence tests remain
  fail-closed.
- Branch coordinates now identify `docs/research.md` and the ArcGIS World
  Geocoding Service separately from KiwiHarvest public address evidence.
  Recipient rows now separate current relationship URLs from general status or
  location URLs, retain FY25 evidence independently, and record 58
  `docs/research.md` coordinate provenances plus 2 `unknown` values. The exact
  54 FY25 and 9 current-public name sets, 3 overlaps, 2 unknown names, and
  reference-only/protected boundaries are tested.
- `ev-mpi-jina-reader` and `ev-mpi-copyright` now have
  `checked_at=2026-08-10T00:00:00+12:00`; their evidence `as_of` remains
  2026-08-09.

### Verification commands and actual results

- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider backend/tests/etl/test_contracts.py backend/tests/etl/test_manifest.py backend/tests/etl/test_extract.py backend/tests/etl/test_woolworths_source.py backend/tests/etl/test_mpi_recalls_source.py backend/tests/etl/test_reviewed_inputs.py -q`: **72 passed**.
- `.venv/bin/ruff format --check backend/app/etl backend/tests/etl`: **passed; 15 files already formatted**.
- `.venv/bin/ruff check backend/app/etl backend/tests/etl`: **passed**.
- `.venv/bin/mypy --cache-dir=/private/tmp/kiwiharvest-phase1-mypy backend/app/etl`: **passed; 7 source files checked**.
- `UV_CACHE_DIR=/private/tmp/kiwiharvest-phase1-uv-cache uv lock --check`:
  **passed; 45 packages resolved**.
- Baseline/allowed-scope check: **passed**; 7 modified existing + 14 new
  allowed files, no out-of-scope changes.

### Pure real-snapshot smoke results

The following smokes used bytes from the supplied local captures and did not
write project artifacts:

- `/private/tmp/woolworths-store-locator-2026-08-10.json`: 353,689 raw bytes,
  raw SHA-256 `dd1bdc1a1093fdd6bb488006cb2576d57cf950d64f1d15e09a0891c278a77cc3`,
  61 records, canonical records SHA-256
  `de02da0a3516e9c56595d4210ac3f8fc1598ca0ba94f2de9a7788f126636415d`, filter
  counts `input=413`, `state_AUK=142`, `division_COUNTDOWN=61`, drift empty.
- `/private/tmp/woolworths-store-locator-2026-08-10-second.json`: 353,689 raw
  bytes, raw SHA-256
  `f9b159f500bbcaa66a813e4c0715a0c0852382b98b2b31d03342f85f6586b15b`, 61
  records, the same canonical records SHA-256
  `de02da0a3516e9c56595d4210ac3f8fc1598ca0ba94f2de9a7788f126636415d`, the
  same filter counts, no duplicates or invalid coordinates, drift empty.
- `/private/tmp/mpi-recalls-reader-2026-08-10.md`: 169,586 raw bytes, raw
  SHA-256 `ffc3c1a89f4e22952be4102ddeb286cdf3148f5fae08c729e958e6d16b24c4c0`,
  exactly 660 records, canonical records SHA-256
  `fdc359115f3670ba4d0af36d94184c3f5856d70572ee6c2ef0ace3636ee7b0e7`, exact
  counts `2016=25, 2017=53, 2018=66, 2019=74, 2020=90, 2021=51, 2022=51,
  2023=68, 2024=88, 2025=57, 2026=37`,
  `source_last_reviewed=2026-07-23`, strict three-field records, and drift
  empty.

### Live CLI results and remaining risk

The explicit CLI was attempted exactly once per source after offline checks:

- `.../.venv/bin/python -m backend.app.etl.extract --source woolworths-store-locator --repo-root /private/tmp/kiwiharvest-phase1-attempt1.1wy3vF`: exit 1 with `HTTP transport failure: [Errno 8] nodename nor servname provided, or not known`.
- The equivalent `mpi-recalled-products` command: exit 1 with the same DNS
  transport error.

Neither command emitted a live report; this is reported as network/provider
unavailability, not as a successful live extraction. The supplied captured
bytes provide the verified real-source parser smoke, while an independently
networked rerun remains the remaining live-provider risk. No test uses live
network, a database session, or a schema/migration dependency.

## Sol final-gate evidence — correction 1 passed (append-only)

This is the later Sol independent final-gate evidence for the same correction;
the earlier local sandbox-DNS result above remains preserved as attempt history.

- Sol inspected all correction files and accepted the implementation,
  schema/provenance boundaries, reviewed truth boundary, and scope.
- Sol's exact offline gate passed: 72 focused pytest tests; ruff format check
  with 15 files already formatted; ruff check; mypy over 7 ETL source files;
  and `uv lock --check` resolving 45 packages.
- Sol's independent real-snapshot parser checks passed for both Woolworths
  captures: 353,689 bytes each; raw SHA-256 values beginning
  `dd1bdc1a1093...` and `f9b159f500bc...`; 61 records each; filter counts
  413/142/61; identical canonical records; and empty drift. MPI passed with
  169,586 bytes, raw SHA-256 beginning `ffc3c1a89f4e...`, 660 records, exact
  per-year counts `25/53/66/74/90/51/51/68/88/57/37`, reviewed date
  `2026-07-23`, and empty drift.
- Sol then ran the explicit live CLI once per source with network access; both
  exited 0. Woolworths reported HTTP 200, 413 input, 142 AUK, 61 COUNTDOWN,
  353,689 raw bytes, raw SHA-256
  `61161f99882fa0a8f8906eb3090f3735fbbaf996f5359bbd5bf361abedff7998`,
  canonical records SHA-256
  `de02da0a3516e9c56595d4210ac3f8fc1598ca0ba94f2de9a7788f126636415d`, the
  explicit missing Content-Type warning, `drift=[]`, and
  `source_last_reviewed=null`. MPI reported HTTP 200, `text/plain`, 660
  records with the exact year counts above, raw SHA-256
  `ffc3c1a89f4e22952be4102ddeb286cdf3148f5fae08c729e958e6d16b24c4c0`,
  canonical records SHA-256
  `fdc359115f3670ba4d0af36d94184c3f5856d70572ee6c2ef0ace3636ee7b0e7`,
  `source_last_reviewed=2026-07-23`, `drift=[]`, and the MPI authority/CC BY
  attribution boundary.
- The successful live CLI created six ignored local artifacts under
  `data/etl/raw/2026-08-09/`: one raw, records, and report file for each
  source. They are local-only inputs for the next phase and are not part of
  the non-ignored project write set.
