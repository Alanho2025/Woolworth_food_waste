# FoodFlow Auckland

Autonomous surplus-food redistribution — a hackathon MVP connecting Woolworths stores, Auckland
community organisations, and delivery drivers.

The product demonstrates one complete journey:

> **Woolworths Donate → AI Match → Driver Route → Partial Acceptance → Automatic Rematch → Completed Delivery**

A Woolworths store donates 60 kg of fresh vegetables. A DeepSeek-powered Google ADK Agent compares
community **need**, **capacity**, category acceptance, storage compatibility, receiving windows, and
route feasibility, then selects a recipient and dispatches a driver. Mid-delivery the recipient can
take only 35 kg. The Agent returns the remaining 25 kg to active inventory, re-compares
alternatives, selects a new recipient, and updates the driver's route — without duplicating a
single kilogram.

The distinction the product exists to make visible: **a community can have urgent need and still be
ineligible, because need and capacity are not the same thing.**

---

## Status

`AGENTS_FoodFlow.md` §2 requires implementation status to be stated honestly. Documentation is
target behaviour until source, tests, and reproducible execution prove otherwise.

| Area | Status |
| --- | --- |
| Typed contracts, clock, error codes, ports | **Implemented** |
| Configuration boundary | **Implemented** |
| Toolchain, dependency pins | **Implemented** — `google-adk` 2.6.3, `litellm` 1.95.0, Python 3.12.13 |
| Domain policies, application layer | **Implemented and tested** — allocation, acceptance, and remainder-only rematch transactions |
| Persistence, seed world | **Implemented and tested** — deterministic SQLite seed with 3 completed and 1 independent in-flight delivery |
| Agent layer, tools, DeepSeek adapter | **Implemented for the MVD** — 18 typed tools, bounded replay journey, incremental visible events, and a thinking-disabled live model factory. The full live Agent journey is configured but not reliability-tested |
| FastAPI surface | **Implemented and tested** — typed donation, match, polling, delivery, confirmation/rematch, dashboard, health, errors, and restricted local CORS |
| Frontend, six screens | **Implemented and browser-tested** — responsive Dashboard through terminal rematch success, generated OpenAPI client, and offline simulated maps |
| Tests, quality gate, E2E harness | **Implemented** — all 15 stages pass; the real-server Playwright journey runs without API interception or core mocks |
| Routing and ETA | **Simulated** — deterministic, hand-traced polylines, labelled in the UI |
| Storage compatibility | **Implemented and tested, not exercised by the demo** (the scenario is entirely ambient) |
| Deadline validation | **Implemented and tested, not meaningfully exercised by the demo** (the pinned clock clears the 19:00 deadline by hours) |
| Live DeepSeek verification | **P0 transport spike verified** — 30/30 successful turns in each arm; thinking-disabled returned 0 reasoning payloads (p95 2.460 s), while provider-default returned reasoning content in 60/60 responses. The P3 model factory is configured, but its full product journey is not live-provider verified; deterministic replay remains the demo path. See `docs/issues/pending-issues.md` ISSUE-002 |

Nothing in this table may be upgraded on the strength of documentation alone.

---

## Stack

| Layer | Choice |
| --- | --- |
| Backend | Python 3.12, FastAPI, Pydantic v2 |
| Persistence | SQLAlchemy 2 + SQLite |
| Agent | Google ADK 2.6.x (one root `FoodRedistributionAgent`) |
| Model | DeepSeek `deepseek-v4-flash`, **non-thinking mode**, `temperature=0` |
| Frontend | Next.js App Router, React, TypeScript strict, Tailwind, TanStack Query, React Hook Form + Zod |
| Map | Stylised local basemap — no network dependency |
| Quality | Ruff, mypy, pytest, tsc, ESLint, Vitest, Playwright |

Two constraints are load-bearing and easy to get wrong:

- **`deepseek-v4-flash` is a choice, not a forced migration.** The legacy `deepseek-chat` and
  `deepseek-reasoner` aliases still resolve — verified by a live probe on 2026-08-08, which
  corrected an earlier finding that claimed they had been retired.
- **Non-thinking mode is mandatory, not a preference.** In thinking mode with `tools`, DeepSeek
  requires `reasoning_content` to be passed back on every subsequent request — which collides with
  three blocker-level no-chain-of-thought rules. Thinking is **enabled by default**, so it must be
  explicitly disabled via `extra_body`.

---

## Running it

```bash
# Python 3.12 toolchain
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"

# From the repository root
npm run data:migrate                         # schema + deterministic demo seed
npm run dev:backend                          # http://localhost:8000
npm run dev:frontend                         # http://localhost:3000
```

Copy `.env_example` to `.env` and fill it in. **`.env` is git-ignored and must never be committed.**

The demo runs without a DeepSeek API key: set `AGENT_TRANSPORT=replay` to use deterministic
recorded fixtures. This is both the test path and the demo-day network fallback. A replay is
always labelled as such in the UI — it is never presented as a live run.

`DEMO_MODE=true` pins the clock to `2026-08-08T15:45+12:00`. Without it, receiving-window checks
run against real wall-clock time and every community is correctly closed outside 16:00–19:00 NZ.

```bash
./scripts/quality_gate.sh    # every gate stage
./scripts/e2e.sh             # isolated DB + both servers + real Playwright journey + teardown
```

---

## Documentation

| Document | Purpose |
| --- | --- |
| [`Requirement.md`](./Requirement.md) | Product specification and the six screens |
| [`AGENTS_FoodFlow.md`](./AGENTS_FoodFlow.md) | Contributor instructions and Definition of Done |
| [`docs/clean_code_spec.md`](./docs/clean_code_spec.md) | Executable engineering contract |
| [`docs/assumption_audit.md`](./docs/assumption_audit.md) | 21 findings against the specification |
| [`docs/phase_review_findings.md`](./docs/phase_review_findings.md) | 34 findings from a three-pass review of the plan |
| [`docs/implementation_phases.md`](./docs/implementation_phases.md) | P0–P8 phase plan and open decisions |
| [`docs/issues/pending-issues.md`](./docs/issues/pending-issues.md) | Issue log and three-attempt limit |

---

## Scope

Deliberately **out of scope** (`Requirement.md` §15, `docs/clean_code_spec.md` §13): production
authentication, RBAC, PostgreSQL, notifications, WebSockets, forecasting, fairness optimisation,
fleet or multi-stop route optimisation, external Woolworths/charity/POS integration, barcode
scanning, image processing, IoT, native mobile apps, and deployment infrastructure.

The MVP prioritises a polished, reliable core journey over architecture for hypothetical future
features.
