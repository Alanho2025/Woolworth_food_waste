# FoodFlow Auckland — Phase Implementation Plan

- **Version:** 2.0 (2026-08-08) — supersedes v1.0. Rewritten after a three-pass review; see [`docs/phase_review_findings.md`](./phase_review_findings.md) for the 34 findings, 9 of which were defects in v1.0.
- **Companion documents:** [`docs/assumption_audit.md`](./assumption_audit.md) (`S-*`/`A-*`/`B-*`/`C-*`/`D-*` findings) and [`docs/phase_review_findings.md`](./phase_review_findings.md) (`R-*` findings, `Q*` questions).
- **Authority:** Sequences work defined by `Requirement.md`, `AGENTS_FoodFlow.md`, and `foodflow_clean_code_spec.md`. Introduces no scope of its own.
- **Each phase carries:** goal · files added/modified · dependencies & setup · implementation details · tests · verification commands · completion criteria · risks, assumptions & decisions · explicitly out of scope.

---

## Codebase inspection

Performed 2026-08-08 against `main` at commit `28b075d`.

| Aspect | State |
| --- | --- |
| Tracked files | 4, all Markdown: `README.md`, `Requirement.md`, `AGENTS_FoodFlow.md`, `foodflow_clean_code_spec.md` |
| Source files | **None.** No `*.py`, `*.ts`, `*.tsx` |
| Manifests / locks | **None.** No `pyproject.toml`, `package.json`, or lock file |
| CI | **None.** No `.github/` |
| `README.md` | One-line stub — `# Woolworth_food_waste` |
| `.gitignore` | Added 2026-08-08 during the audit; previously absent |
| `.env` | Present, untracked, now ignored. Holds a **live DeepSeek key** under the wrong variable name (`DeepSeekAPI_KEY`) |
| Untracked | `.gitignore`, `.env_example`, `docs/*.md` |

**This is a greenfield build.** Every "modified" entry below refers to a file created earlier in this same plan; only the four Markdown files and `.env_example` exist today. Per `AGENTS_FoodFlow.md` §2, all functionality described here is **planned** until source, tests, and reproducible execution prove otherwise.

---

## Phase map

| Phase | Name | Goal | Retires |
| --- | --- | --- | --- |
| **P0** | Foundation & De-risking | Prove the ADK↔DeepSeek path works and the quality gate runs, before product code exists. | S-1, A-1…A-4, B-3, D-2, R-4…R-8, R-22, R-29 |
| **P1** | Domain Core | Every allocation rule as pure, tested Python with no framework imports. | C-1…C-4, C-6, C-7, R-17, R-18 |
| **P2** | Persistence, Seed & Contract Freeze | Give the domain a database, the demo a world, and the frontend an unblocking contract. | C-5, R-3, R-19, R-21, R-26 |
| **P3** | Agent Layer | DeepSeek plans and decides; Python tools are the only path to state. | B-1, D-5, R-1, R-5, R-14, R-28 |
| **P4** | API Surface | Expose the journey as typed, **incrementally observable** events. | D-4, R-2 |
| **P5** | Frontend Foundation — Screens 1–2 | Design system, and a donation from form to Agent. | B-2, R-20 |
| **P6** | Screens 3–4 | Make the Agent's reasoning and the driver's route visible. | D-3, R-7, R-23 |
| **P7** | Screens 5–6 | Land the partial-acceptance and automatic-rematch beats. | R-12, R-24 |
| **P8** | Hardening & Demo Readiness | Prove the journey end to end and make it survive the venue. | D-1, R-11, R-15 |

**Critical path:** P0 → P1 → P2 → { P3 → P4 } ∥ { P5 } → P6 → P7 → P8.

**P5 unblocks after P2, not after P4.** The contract is frozen at P2-8 from the P1 Pydantic models, before any agent code exists — so frontend and agent work proceed concurrently. (v1.0 claimed this parallelism while making P5 depend on a P4 output; see R-3.)

---

## P0 — Foundation & De-risking

### Goal
Prove the two things that would invalidate the whole plan — that ADK 2.x can drive DeepSeek V4 through typed tools reliably, and that the mandated quality gate can actually run — while the repository is still empty enough to change course cheaply.

### Files added
```
pyproject.toml                       package.json
backend/app/config.py                frontend/tsconfig.json
backend/app/__init__.py              frontend/next.config.ts
backend/tests/test_config.py         frontend/eslint.config.mjs
backend/tests/test_architecture.py   frontend/vitest.config.ts
backend/tests/spike/test_deepseek_toolcalls.py
scripts/quality_gate.sh              playwright.config.ts
.github/workflows/ci.yml             docs/issues/pending-issues.md
docs/clean_code_spec.md              (moved from root)
```

### Files modified
`README.md` (stub → real), `.env_example` (1 key → 5), `.gitignore`

### Dependencies & setup
| Package | Pin | Why this pin |
| --- | --- | --- |
| Python | `>=3.12` | `Requirement.md` §10; ADK needs ≥3.10 |
| `google-adk` | `>=2.6.3,<2.7` | Compatible range in manifest, exact in lock (**R-30**) — ADK shipped 2.6.2 and 2.6.3 three days apart |
| `litellm` | `>=1.84` | 1.82.7/1.82.8 are **compromised** releases (**A-2**); current is 1.95.0. Reaches the tree via `google-adk[eval]` regardless of transport choice (**R-6**) |
| `fastapi`, `pydantic` | v2 | `clean_code_spec` §6.1 |
| `sqlalchemy` | `>=2` | §3 |
| `ruff`, `mypy`, `pytest` | latest | §11 |
| Node | `>=20` | Next.js App Router |

Setup: create both venv/node_modules, generate lock files, wire `scripts/quality_gate.sh` so **local and CI call the identical script** (`clean_code_spec` §11).

### Implementation details
- **Config boundary** (`backend/app/config.py`) is the *only* module reading `os.environ`. Pydantic `BaseSettings`. Five variables per `clean_code_spec` §6.4 — `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL`, `DATABASE_URL`, `DEMO_MODE` — plus **`AGENT_TRANSPORT=live|replay`**, split out because one boolean driving both the clock and the model transport violates `clean_code_spec` §5.2 (**R-9**). Missing required vars fail loudly at startup.
- **Architecture test** (`test_architecture.py`) asserts nothing under `backend/app/domain/` imports `fastapi`, `sqlalchemy`, `google.adk`, `litellm`, or `openai`. AST-based, not grep. This is the one architectural rule that erodes silently.
- **The spike** registers three trivial typed tools and runs **two arms**:
  - **Arm A** — `extra_body={"thinking": {"type": "disabled"}}`
  - **Arm B** — default configuration

  30 turns each requiring multi-tool use. Two arms because `deepseek-v4-flash` **defaults to thinking enabled** (**R-4**), and thinking-by-default is independently reported to cause JSON parse failures — a competing explanation for issue #5024 that the original analysis missed (**R-29**). If Arm A is clean and Arm B is not, the "bypass LiteLLM" contingency is unnecessary work.
  - The spike **must assert `reasoning_content` is absent** from Arm A responses. ADK's `LiteLlm` wrapper forwarding `extra_body` through to DeepSeek is **undocumented**, and LiteLLM has a history of silent passthrough failures (#20982, #18039). Absence of an error proves nothing (**R-8**).
  - Kept as a committed test marked `@pytest.mark.skip(reason="P0 spike; unskip to re-measure")` — **not deleted** (**R-16**). The transport decision rests on its numbers and must stay reproducible.
- **Quality gate** wires all fifteen `clean_code_spec` §11 stages. The `agent: core_eval` stage is a **failing placeholder** — `exit 1` with "not implemented until P3" — so it cannot sit green and empty (**R-13**).

### Tests required
`test_config.py` (all six vars load; missing required var raises), `test_architecture.py` (passes clean, fails on a deliberate bad import), the two-arm spike, and one hello-world test per gate stage to prove the stage executes.

### Verification
```bash
git check-ignore -v .env                      # must report ignored
git ls-files | xargs grep -l 'sk-' || echo OK # no key in tracked files
find "$(python -c 'import site;print(site.getsitepackages()[0])')" \
     -name 'litellm_init.pth'                 # R-22: must be empty
pytest backend/tests/spike -v --no-skip       # record both arms' numbers
./scripts/quality_gate.sh                     # all stages run; core_eval fails as designed
```

### Completion criteria
- [ ] `.env` ignored; zero secrets in tracked files; **key rotated** (assume exposure — S-1)
- [ ] `litellm_init.pth` absent from all site-packages (**R-22**)
- [ ] Six env vars load through the single config boundary; missing var fails at startup
- [ ] `AGENTS_FoodFlow.md` §3's three required-reading paths all resolve (**B-3**)
- [ ] Spike ran 30 turns × 2 arms; **failure rate per arm recorded** in `docs/issues/pending-issues.md`
- [ ] Arm A verified to return **no `reasoning_content`** (**R-8**)
- [ ] Transport decision written down with its supporting numbers
- [ ] Quality gate runs every stage; only `core_eval` fails, by design
- [ ] Architecture test proven to fail on a deliberate violation

### Risks, assumptions & decisions
| | |
| --- | --- |
| **Decision** | `DEEPSEEK_MODEL=deepseek-v4-flash`, thinking **explicitly disabled**, `temperature=0`. A choice, not a forced migration — the legacy aliases still resolve (live probe 2026-08-08 corrected **A-1**) |
| **Decision** | Non-thinking is **mandatory, not preferred**: with `tools`, thinking mode requires `reasoning_content` to be passed back on every subsequent request, which collides with three blocker-level no-chain-of-thought rules (**R-1**) |
| **Decision** | Two config flags, not one: `DEMO_MODE` (clock+world) and `AGENT_TRANSPORT` (live/replay) (**R-9**) |
| **Risk** | ADK `LiteLlm` may not forward `extra_body`. **Mitigation:** asserted in the spike; fallback is a direct OpenAI-compatible `BaseLlm` adapter |
| **Risk** | litellm reaches the tree via `google-adk[eval]`, and `core_eval` is a required gate — so it **cannot be avoided** by writing a direct adapter (**R-6**). Pin and monitor |
| **Assumption** | ADK 2.x breaking changes apply: `BaseAgent` subclasses `BaseNode`, `_run_async_impl()` overrides are bypassed, `session.events.append()` unsupported, broad `except` masks retries (**A-3**). Treat all 1.x-shaped tutorials as untrusted |

### Out of scope
No domain logic, no database, no UI, no agent. Deployment, Docker, auth, and PostgreSQL are out of scope for the entire project (`Requirement.md` §15).

**Do not enter P1 until the spike and gate criteria pass.** They are the two that can force a redesign.

---

## P1 — Domain Core

### Goal
Every allocation, eligibility, and quantity rule as pure Python with complete type annotations and zero framework imports. Six of the seven demo-scenario findings are resolved here, because all six are policy questions rather than plumbing questions.

### Files added
```
backend/app/contracts/{donation,community,delivery,driver,agent}.py
backend/app/domain/clock.py                 # Clock protocol
backend/app/domain/quantity.py              # integer-kg value type
backend/app/domain/policies/{eligibility,allocation,partial_acceptance,quantity_integrity}.py
backend/app/domain/routing.py               # deterministic distance/ETA
backend/app/domain/errors.py                # typed error codes
backend/app/domain/delivery_state.py        # state machine
backend/tests/unit/test_*.py                # one per policy
```

### Dependencies & setup
Pydantic v2 and stdlib only. **No new packages.** `zoneinfo` (stdlib) supplies `Pacific/Auckland`.

### Implementation details
- **Contracts** (`clean_code_spec` §4): `DonationRequest`, `FoodItem`, `CommunityOrganisation`, `CommunityRequest`, `Driver`, `DeliveryOrder`, `AllocationDecision`, `RematchDecision`, `AgentRun`, `AuditEvent`. **Need, Capacity, Eligibility, and Agent decision stay four separate concepts** — collapsing them destroys the product's central distinction (`Requirement.md` §9).
- **Quantities are integer kilograms**, enforced at the contract layer (**R-17**). The whole product rests on `available + reserved + in_transit + delivered == 60`; with floats that invariant is not reliably decidable, because the reserve/release/re-reserve cycle can leave a residue that makes a correct system report a violation. Demo values (60/35/25/30/10) are all integers. If fractions are ever needed: `Decimal`, never `float`.
- **`Clock` port** (**C-1**). `DEMO_MODE=true` pins `2026-08-08T15:45:00+12:00`, fifteen minutes before the pickup window opens. Store UTC internally; resolve NZ local through **`ZoneInfo("Pacific/Auckland")`, never a literal `+12:00`** — NZ moves to NZDT on 2026-09-27 and a hardcoded offset silently shifts every window by an hour.
- **Facts before eligibility** (**R-18**). `Requirement.md` §5 requires *every* community card to show an ETA — including B, excluded on category. So the fact-gathering pass computes all displayable facts for all candidates, and eligibility is applied as a **label over a complete fact set, never as an early return**. A short-circuiting validator leaves blank cells in the centrepiece comparison table of the most important pitch screen.
- **Single-destination allocation policy** (**C-2**): *prefer one destination for the full remaining quantity; split only when no single feasible recipient can accept the entire remainder.* **Python-enforced, never a prompt hint** — `clean_code_spec` §2.3 forbids the Agent making final product policy. Without it a correct Agent may allocate 10 kg → C + 15 kg → D, which is a legitimate answer that destroys the scripted "C excluded" beat and fails `Requirement.md` §16.3.
- **Declining-recipient rule** (**C-3**), two parts: (a) reduce the recipient's **declared capacity** to the accepted quantity — A becomes 35 kg, not "60 with 25 freed"; the capacity report was wrong, so correct it rather than unreserving; (b) exclude that recipient from this donation's rematch with `RECIPIENT_DECLINED_THIS_DONATION`. Without this, A shows free capacity at zero travel distance and the Agent may re-select it, loop, and burn its budget on stage.
- **`DeliveryOrder.origin` is an explicit location**, not implicitly the donating store (**C-4**) — the rematched leg departs from Community A where the driver already stands.
- **Quantity-integrity invariant** (**C-7**) asserted at *every* transition, raising a typed error. `AGENTS_FoodFlow.md` §8.4 calls this blocker-level: a test proves one path, an invariant proves all. Expose all four components — `clean_code_spec` §8.4 requires the UI to *display* the proof.
- **Routing** returns polyline length × fixed speed, deterministic, every result carrying `simulated: true` (`AGENTS_FoodFlow.md` §2).
- **Typed errors** per `clean_code_spec` §6.3 plus `RECIPIENT_DECLINED_THIS_DONATION`. Business outcomes are never determined by parsing exception strings.

### Tests required
All eight `clean_code_spec` §10.1 unit groups: category acceptance, storage compatibility, recipient capacity, receiving window, driver capacity, remaining inventory, duplicate-allocation prevention, partial-acceptance arithmetic. Plus regressions pinning **no unrequested split** (C-2), **A never re-selected** (C-3), **integrity raises on duplication** (C-7), and **ETA present for excluded candidates** (R-18). Names state state → action → expected outcome (§10.2).

### Verification
```bash
pytest backend/tests/unit -v
pytest backend/tests/test_architecture.py     # domain imports no framework
sudo date -u 1508030000 && pytest backend/tests/unit -k window   # E1.6, see below
mypy backend/app/domain && ruff check backend/app/domain
```

### Completion criteria
- [ ] `backend/app/domain/` imports no framework (architecture test)
- [ ] All eight §10.1 unit groups pass
- [ ] Quantities are integer kg at the contract boundary; a float input is rejected
- [ ] Regression proves 25 kg goes wholly to D and never splits to C
- [ ] Regression proves A is excluded from rematch after declining
- [ ] Integrity invariant raises on a deliberately duplicated allocation
- [ ] Every candidate — including excluded ones — carries a computed ETA
- [ ] **Window tests pass with the machine clock set to 03:00** ← verify this literally; it is the failure that only appears on stage
- [ ] mypy and Ruff clean

### Risks, assumptions & decisions
| | |
| --- | --- |
| **Decision** | Integer kilograms throughout (**R-17**) |
| **Decision** | Single-destination preferred; split only if no single recipient fits (**C-2**) |
| **Decision** | Declining recipient: capacity corrected **and** excluded from this rematch (**C-3**) |
| **Decision** | Rematch origin is the driver's current location; same driver; no return to store (**C-4**) |
| **Decision** | UI wording for C is *"insufficient for a single-destination allocation"* — a bare "insufficient capacity" is subtly untrue and a judge can challenge it with "but it could take 10 of the 25" |
| **Assumption** | Storage compatibility is implemented and unit-tested but **never exercised by the demo** (all-ambient scenario, B excluded on category). Record in the README status table as *implemented, not exercised* (**C-6**) |
| **Assumption** | Deadline validation is likewise never meaningfully exercised — the pinned 15:45 clock clears the 19:00 deadline by hours (**R-31**). Do not invest UI effort in deadline pressure the scenario never generates |
| **Decision** | A's 60 kg is **declared total capacity**, with remaining capacity tracked separately. Initial state is declared 60 / remaining 60; after reserving 60, remaining is 0; after A reports it can accept only 35 kg, declared becomes 35 and remaining stays 0 because all 35 kg are accepted. User-confirmed 2026-08-08 (**R-25**) |

### Out of scope
No persistence, no I/O, no framework imports, no agent, no UI. No chilled/frozen demo scenario.

---

## P2 — Persistence, Seed & Contract Freeze

### Goal
Give the domain a database, the demo a fully specified deterministic Auckland world, and the frontend a frozen contract so P5 can start.

### Files added
```
backend/app/infrastructure/db/{models,session,repositories}.py
backend/app/application/{allocate_donation,record_acceptance,rematch}.py
backend/app/seed/{communities,drivers,routes,history}.py
backend/app/seed/seed.py                     # idempotent
backend/contracts/openapi.json               # frozen artefact
backend/tests/integration/test_{transaction,persistence,seed}.py
```

### Dependencies & setup
SQLAlchemy 2 + SQLite. No migration tooling — `Requirement.md` §15 defers PostgreSQL work; schema is created from models.

### Implementation details
- **SQLAlchemy models are persistence only** — never used as API response schemas (`clean_code_spec` §4, §9). Pydantic contracts stay independent.
- **Transaction boundary** in the application layer (§6.2): validate inventory → validate recipient capacity → reserve inventory → reserve recipient capacity → create delivery order → create audit event. Any failure rolls back the whole sequence.
  - **Confirmed decision:** success audit inside the transaction; **failure audit written outside it** on a separate connection after rollback. This preserves the evidence `AGENTS_FoodFlow.md` §14 requires without retaining partial product writes (**R-10**). `clean_code_spec` §6.2 is updated in the same change.
- **Seed the world** (**C-5**) — everything `Requirement.md` §1 left undefined: real Auckland coordinates for Woolworths Mount Eden and A/B/C/D; receiving windows for **all four** (only A's is implied); and a genuine need profile for **Community B that is not vegetables** — Screen 3 must display B's Need, and it cannot be the category B rejects.
- **Three drivers**, differing vehicle capacities, **at least one genuinely infeasible for 60 kg**. With one driver, `get_available_drivers` and `validate_driver_capacity` are decorative and `Requirement.md` §10's "choose from feasible drivers" is untrue. Three cost nothing and make two mandated tools real.
- **Hand-traced route polylines** (**R-19**) for each pair actually drawn — Store→A, A→D, and the candidate routes shown on Screen 3. A straight geodesic renders as a line through the Waitematā Harbour and over volcanic cones; to an Auckland judge that reads as broken. Polyline length also feeds a more honest ETA than a straight line.
- **Historical seed** (**R-21/R-26**, confirmed plan default): 2–3 *completed* deliveries so "kilograms rescued" is non-zero on the opening slide, plus one *in-flight* delivery from a different donation so the Dashboard's "active delivery" and "urgent donation" cards are populated. Kept clearly separate from the demo donation so the 60 kg integrity display stays unambiguous.
- **Contract freeze** (**R-3**): export OpenAPI from the P1 Pydantic contracts and commit it. This unblocks P5 **now**, before any agent code exists.

### Tests required
Transaction rollback on constraint failure; persistence round-trip; reservation correctness; seed completeness (every field needed by `calculate_route`, `validate_receiving_window`, and `validate_driver_capacity` is populated for every seeded entity); seed idempotency.

### Verification
```bash
python -m backend.app.seed.seed && sqlite3 foodflow.db .dump | sha256sum
python -m backend.app.seed.seed && sqlite3 foodflow.db .dump | sha256sum   # identical
pytest backend/tests/integration -v
git diff --exit-code backend/contracts/openapi.json                       # frozen
```

### Completion criteria
- [ ] Seed run twice yields byte-identical state
- [ ] A failed allocation leaves zero partial writes; the **failure audit survives**
- [ ] Every field needed by the three geo/time tools is populated for all entities
- [ ] Three drivers seeded, at least one infeasible for 60 kg
- [ ] Route polylines follow plausible roads, not geodesics
- [ ] No SQLAlchemy model appears in any API response type
- [ ] `openapi.json` committed — **P5 is unblocked from here**

### Risks, assumptions & decisions
| | |
| --- | --- |
| **Decision** | Contract frozen at P2, not P4, so frontend runs concurrent with agent work (**R-3**) |
| **Decision** | Three drivers, one infeasible (**C-5**) |
| **Decision** | The demo world contains 2–3 completed deliveries and one independent in-flight delivery. The demo donation's 60 kg ledger remains separately scoped (**Q3/R-26**) |
| **Decision** | Failed allocation attempts are audited durably after rollback in an independent transaction; success audits stay inside the successful transaction. `clean_code_spec` §6.2 updated in the same change (**Q6/R-10**) |
| **Risk** | A second in-flight donation could muddy the 60 kg integrity display. **Mitigation:** scope the integrity widget to the demo donation only |

### Out of scope
No PostgreSQL, no Alembic, no connection pooling, no multi-tenancy, no agent, no UI.

---

## P3 — Agent Layer

### Goal
DeepSeek plans and decides; Google ADK orchestrates a bounded loop; Python tools are the **only** path to state.

### Files added
```
backend/app/agents/{agent,instructions,schemas,model_factory}.py
backend/app/agents/bounds.py                 # timeouts — NOT from RunConfig
backend/app/agents/tools/{read,validate,action}_*.py    # 18 tools
backend/app/infrastructure/deepseek_adapter.py
backend/app/agents/fixtures/                 # replay recordings
backend/tests/agent_eval/test_*.py           # 6 cases
```

### Files modified
`Requirement.md` §11 and `docs/clean_code_spec.md` §7.4 — reconciled tool list (**B-1**), same change, per `AGENTS_FoodFlow.md` §4.

### Dependencies & setup
`google-adk[eval]` (pulls litellm — **R-6**), `litellm>=1.84`. `DEEPSEEK_API_KEY` present for live runs; the fixture path must work without it.

### Implementation details
- **Reconcile the tool list first** (**B-1**). Two documents currently mandate different, non-overlapping sets — 14 vs 16 tools, different names, not a superset relation. Implementing either silently violates §4. **Proposed:** `clean_code_spec` §7.4 naming as the base (more precise vocabulary, satisfies §5.1's one-term rule), plus `assign_driver` and `update_driver_route` from `Requirement.md` §11, dropping `list_available_drivers` for `get_available_drivers`. **18 tools.** Update both documents.
- **Read tools** (`get_donation`, `list_candidate_communities`, `get_community_capacity`, `get_available_drivers`, `calculate_route`) **produce no writes** (§7.4). They return complete fact sets for *all* candidates (**R-18**).
- **Validation tools** delegate to P1 policies — **no rule is reimplemented here**; duplicate allocation logic is a blocker smell (§9).
- **Action tools** idempotent where practical (§7.4).
- **Bounded loop — build the timeouts yourself** (**R-5**). ADK Python's `RunConfig` exposes only `max_llm_calls` (default **500**), `streaming_mode`, `speech_config`, `response_modalities`, `save_live_blob`, `tool_thread_pool_config`, `custom_metadata`. **There is no per-tool timeout and no wall-clock timeout** — the `ToolCallTimeout`/`MaxTurns` fields that v1.0 cited come from `adk-golang`, a third-party Go port, not this SDK. Since `clean_code_spec` §7.1 requires a loop timeout and §7.4 requires one on every I/O tool, implement them: `asyncio.wait_for` around the runner, explicit timeouts inside each I/O tool. Set `max_llm_calls` to ~3× expected, not 500.
- **DeepSeek adapter** — `deepseek-v4-flash`, `temperature=0`, and **`extra_body={"thinking": {"type": "disabled"}}` on every request**. Thinking is **on by default** (**R-4**); leaving it on is slower, returns `reasoning_content`, and independently causes JSON parse failures. All provider code isolated in this one module (`AGENTS_FoodFlow.md` §10). A defensive strip of `reasoning_content` stays at this boundary so nothing leaks even if a future change re-enables thinking.
- **Four-stage validation** of every model output (§7.3): schema → hard constraint → current state → transaction. **No `save_agent_output`-style function** writing model output to product tables (`AGENTS_FoodFlow.md` §7).
- **`AgentStateEvent` persisted incrementally as the run proceeds** — not accumulated and returned at the end. This is what makes P4-3's polling meaningful (**R-2**). All eleven `Requirement.md` §12 states.
- **Fixture replay** (`AGENT_TRANSPORT=replay`): the full journey runs and tests without a live key (`AGENTS_FoodFlow.md` §10). Doubles as the demo-day network fallback. Label a replay honestly in the UI — never present one as live.

### Tests required
Six agent evals (§10.1): selects a feasible recipient; never selects an invalid one; uses correct tools; **re-plans after a typed tool failure**; rematches only the remainder; explanation grounded in tool results. Plus a forced-runaway test proving the loop terminates, and a no-key test proving fixture replay works.

### Verification
```bash
pytest backend/tests/agent_eval -v
DEEPSEEK_API_KEY= AGENT_TRANSPORT=replay pytest backend/tests/integration -v
python scripts/reliability_run.py --runs 30   # records failures + p95 latency
grep -r "reasoning_content" backend/  # only the adapter's defensive strip
```

### Completion criteria
- [ ] Both spec documents list one identical 18-tool set
- [ ] All six agent-eval cases pass; `core_eval` gate placeholder replaced
- [ ] Agent cannot reach the DB except through tools (architecture test)
- [ ] Loop terminates under step **and** wall-clock **and** per-tool budgets
- [ ] Full journey runs with `DEEPSEEK_API_KEY` unset via fixtures
- [ ] No `reasoning_content` in any persisted record, log, or response
- [ ] Events are readable **mid-run**, not only after completion
- [ ] **30-run reliability report** recorded: failure count, p95 wall-clock, each failure classified recovered / visible-error / hung

### Risks, assumptions & decisions
| | |
| --- | --- |
| **Decision** | 30 runs, not 10 (**R-28**). At a true 10% failure rate, a clean 10-run streak occurs **35%** of the time — it would license confidence in a system that fails one demo in ten, and there is one demo. Counting outcomes alone also ignores that a *visible, recovering* failure is survivable on stage while a hang is not |
| **Decision** | **Pre-commit the go-live bar before seeing the data** (**R-14**, Q5): zero hung failures and p95 < 20 s → demo live; otherwise demo on replay with the live path shown afterwards, honestly labelled |
| **Decision** | Non-thinking mode is **mandatory** (**R-1**), not a tuning choice |
| **Risk** | `extra_body` passthrough may fail silently through ADK's wrapper — then the system runs in thinking mode believing it is not, with no symptom but latency. Retired by the P0 spike assertion |
| **Assumption** | DeepSeek enforces no hard rate limits and serves what it can, so peak load degrades into **slowness, not errors** — the failure mode that most threatens the pitch budget (**Q7**) |

### Out of scope
No multi-agent orchestration, no LangChain/LangGraph/CrewAI, no vector DB (`AGENTS_FoodFlow.md` §5). No tools beyond the 18. No human-approval step.

---

## P4 — API Surface

### Goal
Expose the journey over FastAPI as typed events that are observable **while the run is in progress**.

### Files added
```
backend/app/api/{donations,deliveries,agent_runs,dashboard}.py
backend/app/api/errors.py
backend/app/main.py
backend/tests/integration/test_api_*.py
```

### Files modified
`backend/contracts/openapi.json` — regenerated; **must remain backward-compatible** with the P2 freeze or P5 breaks.

### Implementation details
- Endpoints: `POST /donations`, `POST /donations/{id}/match` (returns a run ID immediately), **`GET /agent-runs/{id}`** (events so far + status), `GET /deliveries/{id}`, `POST /deliveries/{id}/confirm`, `GET /dashboard`.
- Routes handle **transport, parsing, DI, and response mapping only** (`AGENTS_FoodFlow.md` §6). Every business decision delegates to an application service.
- **Async run + polling** (**R-2**). v1.0 specified returning the complete event list on run completion *and* streaming events to hide latency — mutually exclusive. Batching is strictly worse than doing nothing: the user watches a spinner for the whole 30–90 s run, then a pre-baked replay, and the eleven visible states arrive *after* the decision they exist to explain. So: `/match` starts the run and returns its ID; the frontend polls `GET /agent-runs/{id}` at ~500 ms and renders events as they land. This still honours `Requirement.md` §15's WebSocket deferral — polling is not WebSocket infrastructure — while actually hiding the latency. Cost is one endpoint and a `refetchInterval`.
- **Typed error responses** mapping P1 error codes to HTTP status plus a machine-readable code. Never a broad catch returning success (§6.3).

### Tests required
Five `clean_code_spec` §10.1 integration tests: donation → agent run; valid match → delivery order; invalid recipient exclusion; partial acceptance → rematch; **rematch creates a new delivery without duplicating quantity**. Plus: polling returns a growing event list mid-run.

### Verification
```bash
uvicorn backend.app.main:app --reload &       # "backend starts" — R-15
curl -sf localhost:8000/health || echo FAIL
pytest backend/tests/integration -v
python scripts/check_openapi_compat.py        # no breaking change vs P2 freeze
```

### Completion criteria
- [ ] All five §10.1 integration tests pass
- [ ] **Backend starts cleanly and serves `/health`** (`Requirement.md` §17, previously unowned — **R-15**)
- [ ] Polling returns a growing event list *during* a run
- [ ] OpenAPI regenerated with no breaking change vs the P2 freeze
- [ ] Every error path returns a typed code, never a 500 with a stack trace
- [ ] No route contains a business rule

### Risks, assumptions & decisions
| | |
| --- | --- |
| **Decision** | Async run + ~500 ms polling. **No WebSocket, no SSE** (**R-2**, **D-4**) |
| **Risk** | Regenerated OpenAPI breaks the P5 client. **Mitigation:** compatibility check in the gate |

### Out of scope
No auth, no rate limiting, no versioning, no pagination, no WebSocket/SSE, no background job queue.

---

## P5 — Frontend Foundation & Screens 1–2

### Goal
Establish the design system and carry a donation from form to Agent.

### Files added
```
frontend/src/app/{layout,page}.tsx
frontend/src/shared/api/generated/            # from openapi.json
frontend/src/shared/ui/{KpiCard,StatusChip,StateBoundary,Attribution}.tsx
frontend/src/features/dashboard/*
frontend/src/features/donate/*
frontend/tests/*.test.tsx
```

### Dependencies & setup
Next.js App Router, TypeScript **strict**, Tailwind, shadcn/ui, TanStack Query, React Hook Form, Zod (`AGENTS_FoodFlow.md` §5). API client **generated** from `backend/contracts/openapi.json` — never hand-maintained (`clean_code_spec` §8.5).

**Entry:** P2 complete. Does **not** require P3 or P4.

### Implementation details
- **Design tokens** per `Requirement.md` §13: deep green primary, warm orange for risk and change, soft neutral background, bold KPI cards, clear status chips, strong hierarchy, minimal prose.
- **Six routes, not seven** (**B-2**). `Requirement.md` §2 says six; the other two documents say seven. "All 60 kg Rescued" is the **terminal state of Screen 6**, matching `Requirement.md` §8. Update the two documents that say seven.
- **`StateBoundary`** renders loading / blocked / retryable-error / completed — mandated by §11.5 and §8.5, and easy to skip until too late.
- **Screen 1, Dashboard** (§3): KPI cards, Auckland map, one urgent donation card, one active Agent decision card, one active delivery card, one capacity-change alert, one impact summary. CTA "Create Donation". Must read as an **active coordination system, not a reporting page**. No analytics beyond the journey (`AGENTS_FoodFlow.md` §11.1).
- **Screen 2, Donate** (§4): nine required fields, step indicator, prefilled-demo button, live validation, **live JSON preview beside the form**, prominent "Submit to AI Agent". No image processing. Transitions directly into Screen 3.
- **OSM attribution** — "© OpenStreetMap contributors" — as a shared component (**R-20**). ODbL-mandated, non-negotiable, appears on every screen carrying a map, whichever tile route P6 chooses.

### Tests required
Donate form produces a JSON preview matching `Requirement.md` §4's structure (snapshot); every primary button dispatches a real action; `StateBoundary` renders all four states.

### Verification
```bash
cd frontend && npx tsc --noEmit && npx eslint . && npx vitest run
npm run build                                  # "frontend build passes" — §17
```

### Completion criteria
- [ ] `tsc --strict` and ESLint clean; production build passes
- [ ] Submitting the form creates a real donation and navigates to Screen 3
- [ ] JSON preview matches §4's example structure
- [ ] **Every primary button performs a real action** — a dead primary button blocks completion (§11.5, §9)
- [ ] No backend eligibility rule reimplemented in React (§9)
- [ ] OSM attribution present wherever a map renders

### Risks, assumptions & decisions
| | |
| --- | --- |
| **Decision** | Six routes; success is Screen 6's terminal state (**B-2**) |
| **Decision** | API client generated, never hand-written |
| **Risk** | Built against the P2 contract before P4 exists — drift possible. **Mitigation:** P4's compatibility check |
| **Open** | **R-12 — is the Dashboard live throughout the demo, or only the opening slide?** Live is far more convincing and needs a refetch strategy decided *here*, not retrofitted in P7 |

### Out of scope
No auth UI, no settings, no admin, no analytics dashboards, no i18n, no mobile-native. Screens 3–6 are P6/P7.

---

## P6 — Screens 3–4

### Goal
Make the Agent's reasoning and the driver's route visible. Screen 3 is the most important pitch screen.

### Files added
```
frontend/src/features/agent-match/{AgentPlan,CommunityCompare,FinalDecision}.tsx
frontend/src/features/driver-route/{DriverPanel,RouteMap,InstructionCard}.tsx
frontend/src/shared/map/{BaseMap,tiles/}      # bundled basemap
frontend/tests/agent-match.test.tsx, driver-route.test.tsx
```

### Dependencies & setup
Leaflet or MapLibre. **Basemap assets generated locally** — see below.

### Implementation details
- **Screen 3** (§5), three sections: **Agent Plan** (six concise steps), **Community Comparison** (four cards: need, remaining capacity, category compatibility, opening status, **ETA**, final status), **Final Decision** (selected org, quantity, driver, distance, ETA, prominent explanation, "Delivery Order Created").
- **Need and Capacity render as visually distinct elements** (§9). *A community can have high demand and still be excluded for lacking capacity* — this distinction **is** the product's value proposition, and if the two render as similar-looking numbers the pitch does not land.
- **All four cards show an ETA, including excluded ones** (**R-18**). Blank cells in the centrepiece comparison table read as bugs.
- **Exclusion wording for C** is *"insufficient for a single-destination allocation"*, per P1's policy.
- **Only plan, checked facts, exclusions, and decision.** Never chain-of-thought (§5, §7.3). **Not a chatbot transcript** (§11.2).
- **Poll P4's `GET /agent-runs/{id}`** at ~500 ms and reveal states as they arrive (**R-2**). All eleven §12 states. No debug logs in the demo interface.
- **Screen 4** (§6): mobile-style driver panel beside a larger Auckland map — route polyline, driver marker, pickup/destination markers, current load card, instruction card, "Read Instructions Aloud" (`SpeechSynthesis`), "Arrived at Recipient".
- **Route visibly labelled simulated** (§6, `AGENTS_FoodFlow.md` §2).
- **Basemap without a network dependency** (**D-3**, **R-7**). v1.0 proposed bundling an OSM raster subset — the OSMF Tile Usage Policy **explicitly prohibits** offline use and bulk/prefetch downloading of `tile.openstreetmap.org`, so that mitigation was a licence violation. Legitimate routes, cheapest first: **(a) a stylised SVG basemap** traced from an Auckland coastline extract — almost certainly sufficient for this pitch; (b) self-generated MBTiles from an OSM extract via OpenMapTiles, served locally; (c) a provider whose terms permit offline caching. Markers, polyline, and driver animation are our own geometry regardless. **Attribution remains mandatory in all three.**

### Tests required
Screen 3 shows excluded and selected communities with reasons; all four cards carry an ETA; no raw reasoning in the DOM; the timeline replays all eleven states; Screen 4 shows the correct delivery.

### Verification
```bash
cd frontend && npx vitest run
# then, literally: disable Wi-Fi, reload Screens 3 and 4
```

### Completion criteria
- [ ] Four communities render with **distinguishable** Need and Capacity
- [ ] B, C, and A each display their specific exclusion reason
- [ ] Every card shows an ETA, including excluded ones
- [ ] No raw reasoning text anywhere in the DOM
- [ ] **Map renders correctly with the network disabled** ← turn the Wi-Fi off and reload
- [ ] OSM attribution visible
- [ ] Text-to-speech fires on click
- [ ] Timeline reveals states **progressively during** the run, not after it

### Risks, assumptions & decisions
| | |
| --- | --- |
| **Decision** | Stylised SVG basemap as default; self-generated MBTiles only if a real basemap proves necessary. **Never bulk-download OSM tiles** (**R-7**) |
| **Open** | **Q4 — driver animation: auto-play with time compression, or manual advance?** (**R-23**) A real drive is 15–25 min against a 2–3 min demo budget, so compression is unavoidable if it auto-plays. **Recommended: manual advance** via the "Arrived at Recipient" button §6 already specifies, with a short looping progress animation — less build, and it keeps the presenter in control of pacing |
| **Risk** | `SpeechSynthesis` needs a user gesture in some browsers and loads voices asynchronously. A silent button is a §9 blocker. **Mitigation:** fire on click only; render a visible fallback if no voice resolves |

### Out of scope
No real GPS, no commercial routing, no turn-by-turn, no multi-stop optimisation, no traffic data, no offline-first PWA.

---

## P7 — Screens 5–6

### Goal
Land the two pitch beats the whole product exists to demonstrate. Screen 6 is the second most important screen.

### Files added
```
frontend/src/features/delivery-confirmation/*
frontend/src/features/rematch/{RematchTimeline,RouteDiff,IntegrityBar,SuccessState}.tsx
frontend/tests/{delivery-confirmation,rematch}.test.tsx
```

### Files modified
`frontend/src/features/dashboard/*` — **revisited** so the Dashboard reflects state this phase produces (**R-12**).

### Implementation details
- **Screen 5** (§7): full / partial / rejected; planned 60 kg; accepted input (35 kg); **remaining auto-calculated to 25 kg**; reason field; visible warning that the remainder returns to active inventory; primary button "Confirm and Rematch Remaining Food".
- **The quantity change is visually obvious** — before/after display or progress bar (§7), not a number that quietly changes.
- **Confirm triggers the rematch automatically** (**R-24**). `AGENTS_FoodFlow.md` §21 requires that no routine human approval is introduced, so on click the Agent runs immediately and Screen 6 loads *live*. A second click to start would contradict the autonomy claim the pitch makes — and is what a developer building screen-by-screen naturally produces, so it is called out here explicitly.
- **Screen 6** (§8) as a staged timeline, all eight steps: 35 kg accepted → 25 kg returned → alternatives rechecked → B excluded → C excluded → D selected → route updated → new order created.
- **Old route vs new route** on the map. The new leg departs from **Community A, not the store** (**C-4**) — a store-origin route draws a phantom return trip to Mount Eden.
- **Integrity bar** (**C-7**, **R-17**): `clean_code_spec` §8.4 requires the UI to *show* that no quantity was duplicated. Render P1's four components — available / reserved / in transit / delivered — as a stacked bar summing to 60 kg throughout. This converts a correctness requirement into the single most convincing visual in the pitch.
- **Terminal success state: "All 60 kg Rescued."**
- **Emphasis on recovery, not error** (§8). Warm orange signals change, never failure.
- **Dashboard revisited** (**R-12**): §3 requires "food currently in transit" and "one alert showing a community capacity change" — both produced *here*, while the Dashboard was built and closed in P5. Wire the refetch decided in P5.

### Tests required
35 kg input yields exactly 25 kg remaining; timeline shows all eight steps in order; new route originates at Community A; integrity bar sums to 60 kg at every stage; success state reads "All 60 kg Rescued"; the Dashboard reflects the capacity-change alert after confirmation.

### Verification
```bash
cd frontend && npx vitest run
# manual: complete the journey, then navigate back to the Dashboard
```

### Completion criteria
- [ ] Entering 35 kg yields exactly 25 kg, no rounding drift (integer kg — **R-17**)
- [ ] Rematch fires **automatically** on confirm, with no second click
- [ ] Timeline shows all eight steps in order
- [ ] New route visibly originates at Community A
- [ ] Integrity bar sums to 60 kg at every stage of the journey
- [ ] Success state reads "All 60 kg Rescued"
- [ ] **Dashboard reflects post-rematch state** when revisited

### Risks, assumptions & decisions
| | |
| --- | --- |
| **Decision** | Confirm → automatic rematch, single click (**R-24**) |
| **Decision** | Dashboard is revisited here rather than left stale (**R-12**) |
| **Open** | **R-27 — what Need does Community A display after declining?** An unchanged "urgent need" beside "declined 25 kg" invites a question the presenter cannot answer cleanly |

### Out of scope
No rejection-path UI beyond the option itself (the demo uses partial acceptance), no multi-round rematch, no driver reassignment, no notifications.

---

## P8 — Hardening & Demo Readiness

### Goal
Prove the whole journey end to end, then make it survive a real room.

### Files added
```
e2e/{harness.ts,journey.spec.ts}
scripts/{e2e.sh,reset_demo.sh,reliability_run.py}
```

### Files modified
`README.md` — final implemented / simulated / configured-but-unverified / planned status table.

### Implementation details
- **Build the E2E harness** (**R-11**). v1.0 had P0 own "Playwright runs" and P8 own "the journey passes", with **nobody owning "both servers and a seeded database come up together reproducibly"** — the classic phase-seam gap, and it surfaces at the worst possible time. `scripts/e2e.sh` starts FastAPI, starts Next.js, seeds the DB, waits for both health checks, runs Playwright, tears down. Agent behaviour pinned via `AGENT_TRANSPORT=replay` so the test is deterministic; a separate live smoke run covers the real path.
- **The one mandatory E2E test** (§16, §10.1): Donate → Agent Match → Driver Route → Partial Acceptance → Automatic Rematch → Completed Delivery, asserting all ten numbered §16 checks including **final delivered quantity equals exactly 60 kg**.
- **Timed rehearsal** (**D-1**). Budget is 2–3 min (§26). Two Agent runs of multiple round-trips each plausibly consume 30–90 s. Measure it. Levers if over: P4's progressive reveal (already hiding most of it), and replay.
- **Failure-mode rehearsal.** Kill the network mid-run; let a DeepSeek call time out; submit an invalid donation. **The system degrades visibly and honestly** — §9 makes a dead primary button a blocker, and a frozen screen in front of judges is worse.
- **README status table** (`AGENTS_FoodFlow.md` §19) names plainly: simulated routing; storage compatibility *implemented, unit-tested, not exercised* (**C-6**); deadline validation likewise (**R-31**); and any replay path used in the demo.
- **`reset_demo.sh`** — one command back to the exact starting state, run between rehearsals and between judging sessions.

### Tests required
The E2E journey from a clean seed; two consecutive full rehearsals from reset; the complete §11 quality gate.

### Verification
```bash
./scripts/e2e.sh                              # both servers + seed + Playwright + teardown
./scripts/quality_gate.sh                     # all 15 stages
./scripts/reset_demo.sh && ./scripts/e2e.sh   # twice, consecutively
git log -p | grep -iE 'sk-[a-zA-Z0-9]{20,}' || echo "no secrets in history"
```

### Completion criteria
- [ ] E2E passes from a clean seed
- [ ] Timed rehearsal completes **within 3 minutes**
- [ ] All fifteen §11 gate stages pass, or are explicitly reported as unverified
- [ ] Final delivered quantity is exactly 60 kg with no duplication
- [ ] Zero secrets in history, bundle, logs, fixtures, or screenshots
- [ ] Every `Requirement.md` §17 criterion individually confirmed, including **"the backend starts"**
- [ ] Two consecutive rehearsals from reset both succeed
- [ ] README status table matches runtime evidence

### Risks, assumptions & decisions
| | |
| --- | --- |
| **Decision** | E2E runs on `AGENT_TRANSPORT=replay` for determinism; live path covered by a separate smoke run |
| **Risk** | **DeepSeek surge pricing doubles rates during Beijing 09:00–12:00 and 14:00–18:00 — NZST 13:00–16:00 and 18:00–22:00**, covering a typical judging slot. Not active as of 2026-08-02 but may activate. The real threat is **latency, not cost**: DeepSeek enforces no hard rate limits and serves what it can, so peak load degrades into slowness (**Q7**) |
| **Risk** | Venue network. **Mitigation:** bundled basemap (P6) + replay transport (P3) |
| **Assumption** | Honest reporting throughout — `AGENTS_FoodFlow.md` §20 forbids claiming live verification when only fixtures ran |

### Out of scope
No deployment, no Docker, no hosting, no monitoring, no load testing, no accessibility audit beyond what shadcn/ui provides, no security review beyond the secret scan.

---

## Standing rules

From `AGENTS_FoodFlow.md` §13, applying throughout rather than at any single phase:

1. **Report honestly.** Name the exact commands run and their real results. State what was *not* verified — especially live DeepSeek calls and browser checks. Never write "tests passed" without the output (§20).
2. **Three-attempt limit.** For anything touching correctness, quantity integrity, Agent behaviour, state transitions, or test gates: log it in `docs/issues/pending-issues.md` with root cause, hypothesis, change, result, evidence. **After three failed substantive attempts on one root cause, stop and report the blocker.** Never lower a gate to make something pass (§14).
3. **Ask before deciding product direction.** Conflicts changing scope, matching responsibility, data ownership, or public contracts go to the user (§4).
4. **Update source-of-truth documents in the same change** that alters the behaviour they describe (§4, §19).
5. **Smallest complete vertical slice first.** Abstractions follow real duplication (§6).
6. **Simulated is labelled.** Routing, ETA, and any replay are visibly marked in the UI (§2).

---

## Open decisions

Implementation proceeds on the recommendation unless overridden. Cost of overriding rises sharply once the phase begins.

| # | Decision | Recommendation | Locks at |
| --- | --- | --- | --- |
| 1 | DeepSeek model & mode | `deepseek-v4-flash`, thinking **explicitly disabled**, `temperature=0` | P0 |
| 2 | Rotate the exposed key | Yes — assume exposure | P0 |
| 3 | LiteLLM vs direct adapter | From the two-arm spike; note litellm arrives via `[eval]` either way | P0 |
| 4 | Config flags | `DEMO_MODE` and `AGENT_TRANSPORT` split | P0 |
| 5 | Quantity type | **Integer kilograms** | P1 |
| 6 | Allocation strategy | Single destination preferred; split only if no single recipient fits | P1 |
| 7 | Declining recipient | Capacity corrected **and** excluded from this rematch | P1 |
| 8 | Rematch origin | Driver's current location; same driver; no return to store | P1 |
| 9 | Demo clock | `Clock` port; `DEMO_MODE` pins `2026-08-08T15:45+12:00`; `Pacific/Auckland`, never a literal offset | P1 |
| 10 | A's 60 kg capacity semantics | **Declared total 60, remaining tracked separately; after accepting 35: declared 35 / remaining 0.** User-confirmed 2026-08-08 | P1 |
| 11 | Driver seed | Three drivers, one infeasible for 60 kg | P2 |
| 12 | **Pre-existing demo activity?** | Recommended: 2–3 completed + 1 in-flight, scoped away from the 60 kg display | P2 |
| 13 | Durable failure audit | **Yes — after rollback in an independent transaction; success audit remains atomic with success writes.** | P2 |
| 14 | Go-live reliability bar | 30 runs; zero hangs, p95 < 20 s → live; else replay | P3 |
| 15 | Event transport | Async run + ~500 ms polling. No WebSocket/SSE | P4 |
| 16 | Screen count | Six routes; success is Screen 6's terminal state | P5 |
| 17 | Dashboard liveness | Recommended: live, refetched after journey events | P5 |
| 18 | **Driver animation** | Recommended: manual advance + looping progress animation | P6 |
| 19 | Basemap | Stylised SVG default. **Never bulk-download OSM tiles** | P6 |

**Blocking everything: Q1 — the deadline and team size are unknown.** As specified this plan is roughly **60–100 focused engineering hours**. For four people over a weekend that is tight but real; for one person over 48 hours it is not achievable, and the right response is to cut scope deliberately now. A shorter working journey beats nine well-planned phases of which six get finished.
