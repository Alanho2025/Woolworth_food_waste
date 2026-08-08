# Requirement-derived edge-test matrix

Status: **test plan only unless a row explicitly cites an executed test**. This file does not
claim that a planned phase or product journey is implemented.

Sources: `Requirement.md` sections 16-17, `docs/clean_code_spec.md` sections 10-11, and
`docs/implementation_phases.md` v2.0. Core policy, application, persistence, transaction, state,
quantity, and API paths must not be mocked. Only external provider boundaries such as DeepSeek,
network routing, and speech may use a clearly labelled replay or fixture.

## P0 failure matrix — initial audit

Point-in-time audit performed 2026-08-08 before the P0 implementation worker finished. Every
failure must be re-run after its owner lands changes.

| Gate stage | Exact evidence | Initial result |
| --- | --- | --- |
| backend / format | `.venv/bin/ruff format --check backend` | **Fail:** 9 files would be reformatted |
| backend / lint | `.venv/bin/ruff check backend` | **Fail:** 12 errors |
| backend / typecheck | `.venv/bin/mypy backend/app` | Pass: no issues in 35 source files |
| backend / tests | `.venv/bin/pytest -v` | **Fail:** 26 failed, 40 passed, 1 xfailed; failures were incomplete P1 eligibility wiring, not a reason to weaken P0 |
| frontend / format | quality-gate stage/script | **Missing:** no formatter script or `scripts/quality_gate.sh` at audit time |
| frontend / lint | `npm run lint` | **Fail:** unused `AgentRun` import |
| frontend / typecheck | `npm run typecheck` | **Fail:** invalid Next config `eslint` property and unused `AgentRun` import |
| frontend / tests | `npm test` before test addition | **Fail:** no test files, exit 1. After adding `frontend/tests/p0-foundation.test.ts`: 1 file/1 test passed |
| agent / schema validation | quality-gate inventory | **Missing:** no executable stage/test at audit time |
| agent / bounded-loop check | quality-gate inventory | **Missing:** source bounds existed but no executable gate proof |
| agent / core eval | quality-gate inventory | **Missing:** must be an intentional failing P0 placeholder, not green or absent |
| architecture / forbidden imports | `.venv/bin/pytest backend/tests/test_architecture.py -v` | Pass. An isolated copied tree with a deliberate `import sqlalchemy` produced the required red result: 1 failed, naming the violating file/import |
| architecture / dependency cycles | same architecture command | Pass, including a deliberate synthetic cycle detector test |
| security / secret scan | `git check-ignore -v .env`; `git ls-files -z \| xargs -0 grep -Il 'sk-'`; `find .venv -name 'litellm_init.pth' -print` | Manual checks pass: `.env` ignored, no tracked match printed, no persistence artefact. **Executable gate stage still missing** |
| journey / end-to-end core flow | quality-gate inventory | **Missing by phase:** P0 may prove the real browser runner, but must not pretend the P8 product journey exists |

Additional P0 blockers observed in the initial audit:

- `backend/tests/spike/test_deepseek_toolcalls.py` was absent.
- `.venv/bin/pytest backend/tests/spike -v --no-skip` failed before collection because
  `--no-skip` was unrecognised. The committed default-skip and explicit-unskip path both need an
  executable proof. No live call was made.
- `scripts/quality_gate.sh`, `.github/workflows/ci.yml`, root `package.json`, root
  `playwright.config.ts`, and a Python lock file were absent.
- The installed critical versions were `google-adk==2.6.3` and `litellm==1.95.0`; the compromised
  LiteLLM versions were not installed.
- API-key rotation remains a human-owned security action and cannot be inferred from a test.

## Planned non-mock edge tests by phase

### P1 — real domain policy and contract path

These call Pydantic contracts and the real domain functions directly. A pinned `Clock` and a
deterministic route fixture are permitted provider inputs; allocation, eligibility, state, and
quantity functions are never replaced.

| Requirement-derived case | Real path and expected proof |
| --- | --- |
| Donation JSON boundary | Construct the real `DonationRequest`; reject zero, negative, fractional kilograms, empty items, invalid window, and naive/invalid timestamps before any use case runs |
| Community B unsupported vegetables | `assess_candidates` computes all facts first, then reports `RECIPIENT_CATEGORY_UNSUPPORTED`; B still has a route/ETA for its card |
| Community C insufficient capacity | Real assessment rejects C for both 60 kg and remaining 25 kg when capacity is 10 kg; exactly-equal capacity remains feasible |
| Storage/window/deadline hard constraints | Independently isolate each real rule so its typed code is observable; test closed `is_open`, ETA on both sides of the receiving-window boundary, hostile 03:00 machine time, DST, and deadline equality/overrun |
| Single destination before split | Real `plan_allocation` sends all 60 kg to A and all remaining 25 kg to D when each can take the whole amount; C must not receive a 10 kg split |
| Split only when necessary | With no single feasible recipient, real allocation may split, covers the exact integer remainder, and never exceeds any recipient capacity |
| Driver constraints | Real validation rejects unavailable and undersized drivers; capacity exactly equal to the order is accepted |
| Quantity conservation | Exercise real reserve, dispatch, deliver, release, return, and re-reserve transitions; every state satisfies `available + reserved + in_transit + delivered == total` |
| Duplicate prevention | A second reservation/allocation of already-reserved quantity raises `DUPLICATE_ALLOCATION` or the specific typed inventory error without changing the original ledger |
| Partial acceptance arithmetic | Real policy covers accepted values `0`, `35`, `60`, and rejects `-1`, `61`, and fractional values; only 25 kg returns after accepting 35 kg |
| Declining recipient | Real policy corrects A's declared capacity to 35 kg and emits `RECIPIENT_DECLINED_THIS_DONATION`, preventing A from being selected again |
| Delivery state machine | Every permitted transition succeeds; skips, backwards transitions, and a second terminal confirmation raise `INVALID_STATE_TRANSITION` |

### P2 — real application services, UoW, repositories, and isolated SQLite

Each test creates a temporary on-disk SQLite database, calls `create_all`, seeds through the real
seed function/repositories, builds `SqlAlchemyUnitOfWork`, and queries persisted rows afterward.
No in-memory repository, fake UoW, repository mock, or policy mock is allowed.

| Requirement-derived case | Real path and expected proof |
| --- | --- |
| Idempotent deterministic seed | Seed the same temp DB twice; row counts and stable business records are unchanged, and the world contains A/B/C/D plus genuinely feasible/infeasible drivers |
| Valid 60 kg match to order | Real `AllocateDonation.execute` reserves inventory/capacity and persists one 60 kg A delivery plus success audit in one transaction |
| Invalid recipient rollback | Select B, C, closed, or over-capacity recipient through the real use case; inventory, recipient capacity, order count, and success audit remain unchanged while the separately committed failure audit is present |
| Driver and route persisted | A feasible real driver is assigned and the simulated route is round-tripped through SQLite without losing origin, destination, ETA, or polyline |
| Idempotent allocation retry | Repeat the same command/idempotency identity; no second order, reservation, or audit side effect is created |
| Partial acceptance 35/25 | Real `RecordAcceptance.execute` advances state, persists 35 delivered and 25 available, changes A capacity to 35, and writes the audit atomically |
| Invalid acceptance rollback | Accept `-1`, `61`, or confirm an invalid/terminal state; delivery, ledger, capacity, and audits prove the transaction did not partially mutate state |
| Rematch to D | Real `RematchRemaining` excludes A and C, creates exactly one 25 kg D order, keeps the same driver, and persists origin as Community A rather than the store |
| Rematch failure rollback | Force a real constraint failure using database state (not an exception mock); the 25 kg remains available and no partial order/reservation survives |
| Final quantity and no duplication | Complete the second order through real services; persisted ledger is `0 + 0 + 0 + 60`, orders total 60 kg, accepted quantities total 60 kg, and no row represents the same 25 kg twice |
| SQLite integrity and concurrency edge | Two real sessions attempt conflicting reservation/confirmation; database/application protection permits one valid result and preserves the 60 kg invariant |

### P3 — bounded Agent with only external-model replay

DeepSeek may be replaced by an explicitly labelled recorded replay. The replay must emit tool
requests into the real tool implementations, real application services, and real temp SQLite.

| Requirement-derived case | Real path and expected proof |
| --- | --- |
| Feasible selection | Recorded model output selects A; real tools revalidate and persist the order |
| Invalid selection | Recorded output selects B/C; real validation rejects it and no state is written |
| Tool order and typed failure recovery | Trace proves the bounded loop used required real tools and replanned after a real typed validation failure |
| Remaining-only rematch | Replay proposes rematch after 35 accepted; real tools expose and allocate exactly 25 kg, never 60 kg |
| Explanation grounding | Concise explanation contains only facts returned by tools and no hidden reasoning/provider internals |
| Bounds | Step, run-time, and per-tool budgets terminate with typed errors; do not simulate core decisions to obtain the timeout |

### P4 — real FastAPI route to real SQLite

Use `TestClient`/ASGI transport against the real application dependency graph pointed at a temp
SQLite URL. Overriding only the database URL, clock, and external Agent/model provider is allowed;
API routes, services, repositories, UoW, and policies are real.

| Requirement-derived case | Real path and expected proof |
| --- | --- |
| Donation submission JSON | `POST /donations` validates and persists a real donation; malformed/zero/fractional payload returns the typed 4xx response and creates no rows |
| Incremental Agent run | Start matching and poll real persisted run events; event count grows and sequence is monotonic rather than appearing only after completion |
| Match/detail routes | The API exposes B/C exclusions, A selection, real delivery/driver/route, and an ETA for every candidate |
| Partial confirmation starts rematch | One `POST /deliveries/{id}/confirm` records 35/25 and returns a non-null rematch run id; no second approval endpoint is needed |
| Typed errors and not-found edges | Unknown donation/order/run and invalid transition return stable error codes without leaking tracebacks, keys, or provider detail |
| Read endpoints are read-only | Repeated dashboard/detail/run polling leaves all database row values and audit counts unchanged |

### P5-P7 — visible behaviour with real frontend state boundaries

Frontend component tests may stub HTTP at the network boundary, but fixtures must validate against
the runtime schemas and must be labelled as API fixtures. They may not reimplement eligibility or
quantity policy in React.

| Requirement-derived case | Expected visible proof |
| --- | --- |
| Donate | Valid form emits the required JSON preview; invalid quantity/window blocks submission with accessible feedback |
| Agent Match | A is selected; B/C remain visible with distinct typed exclusion reasons, Need and Capacity are separate, and every card shows ETA |
| Driver Route | Correct 60 kg order, driver, explicit route, simulated label, deadline, and speech control are visible |
| Partial acceptance | Entering 35 displays planned 60, accepted 35, remaining 25 and triggers rematch once |
| Rematch | D and 25 kg appear, A/C exclusions remain explainable, old/new routes differ, and no UI-side allocation calculation claims authority |
| Error/loading states | Loading, blocked, retryable error, and completed states remain distinct; primary buttons work exactly once under double-click/retry |

### P8 — complete real journey

Run Playwright against the real frontend and backend with isolated temp SQLite. The only replay is
the explicitly labelled DeepSeek provider recording; every tool, policy, transaction, route,
state transition, API handler, and UI interaction is real.

| Requirement 16/17 checkpoint | End-to-end assertion |
| --- | --- |
| 1. Donation produces valid JSON | Submit through the UI and verify both preview and persisted API response |
| 2-4. B/C excluded, A selected | Observe all candidate cards and typed reasons, then the 60 kg A decision |
| 5. Driver and route created | Observe the persisted order, correct driver, Auckland route, and simulated label |
| 6-7. 35 accepted, 25 remains once | Confirm 35 through the UI; verify the visible equation and query the backend ledger/order totals |
| 8-9. D selected and route updates | Wait for automatic rematch, then verify D, the same driver, A-origin route, and visible old/new route change |
| 10. Final delivered is 60 | Complete D; verify final UI result and persisted `0 + 0 + 0 + 60` invariant |
| Completion resilience | Refresh at each major screen, double-click action buttons, and retry a failed poll; the persisted journey remains idempotent and finishable in the required 2-3 minute path |

