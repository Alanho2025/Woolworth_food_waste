# FoodFlow Auckland — Assumption Audit

- **Date:** 2026-08-08
- **Audited documents:** `Requirement.md`, `AGENTS_FoodFlow.md`, `foodflow_clean_code_spec.md`
- **Purpose:** Verify that every assumption embedded in the specification still holds against (a) external reality in August 2026, (b) the other specification documents, and (c) the demo scenario's own arithmetic and state machine.
- **Status of this document:** Analysis only. No runtime code exists yet. Every "implemented" claim in this repository is currently **planned**, per `AGENTS_FoodFlow.md` §2.

Findings are graded:

| Grade | Meaning |
| --- | --- |
| **BLOCKER** | The specification as written cannot be implemented, or will fail at runtime / on stage. Must be resolved before the phase that depends on it. |
| **CONFLICT** | Two source-of-truth documents disagree. `AGENTS_FoodFlow.md` §4 requires explicit resolution, not silent choice. |
| **GAP** | A required behaviour has no defined rule or data. Implementation would have to invent it, which `AGENTS_FoodFlow.md` §8.1 forbids. |
| **RISK** | Implementable as written, but likely to fail under demo conditions. Needs a mitigation owner. |

---

## 0. Summary

| ID | Grade | Title | Blocks |
| --- | --- | --- | --- |
| S-1 | **BLOCKER** | Live API key in `.env`, not git-ignored (mitigated 2026-08-08) | P0 |
| A-1 | ~~BLOCKER~~ **CORRECTED** | Retirement claim **disproved by live probe**; the real constraint is thinking-on-by-default | P0, P3 |
| A-2 | **BLOCKER** | LiteLLM 1.82.7 / 1.82.8 are compromised releases; LiteLLM is not an ADK extra | P0, P3 |
| A-3 | **BLOCKER** | ADK 2.x is a breaking-change platform; most tutorials show retired 1.x patterns | P0, P3 |
| A-4 | **RISK** | DeepSeek + LiteLLM + ADK multi-tool-call parsing is a known intermittent failure | P0, P3 |
| B-1 | **CONFLICT** | Two incompatible tool lists (14 vs 16 tools, different names) | P3 |
| B-2 | **CONFLICT** | "Six screens" vs seven screens | P5 |
| B-3 | **GAP** | `AGENTS_FoodFlow.md` §3 points at files that do not exist | P0 |
| C-1 | **BLOCKER** | No frozen demo clock — receiving-window checks fail outside 16:00–19:00 NZ | P1 |
| C-2 | **BLOCKER** | Nothing stops the Agent from splitting 25 kg across C **and** D | P1 |
| C-3 | **BLOCKER** | Nothing stops the Agent from re-selecting Community A on rematch | P1 |
| C-4 | **GAP** | Rematch delivery's pickup origin is undefined | P1, P6 |
| C-5 | **GAP** | Seed data is under-specified (coordinates, windows, drivers, B's needs) | P2 |
| C-6 | **GAP** | Storage compatibility is required but never exercised by the demo | P1 |
| C-7 | **GAP** | Quantity integrity is written as a test, not as an invariant | P1 |
| D-1 | **RISK** | LLM round-trip latency vs the 2–3 minute pitch budget | P3, P8 |
| D-2 | **RISK** | Quality gate is heavy for a hackathon timeline | P0 |
| D-3 | **RISK** | Map tiles are an external network dependency | P6 |
| D-4 | **GAP** | Animation transport (WebSocket vs replay) left undecided | P4 |
| D-5 | **RISK** | DeepSeek V4 thinking mode emits reasoning the spec forbids surfacing | P3 |

---

## 1. Security

### S-1 — BLOCKER — Live API key in `.env`, not git-ignored

**Observed.** The working tree contains `.env` holding a real DeepSeek key under the variable name `DeepSeekAPI_KEY`. The repository had **no `.gitignore`**, so `.env` was untracked but not ignored — a single `git add -A` would have committed a live credential to a public GitHub repository.

**Also non-conforming.** The variable name `DeepSeekAPI_KEY` does not match the contract in `foodflow_clean_code_spec.md` §6.4, which requires `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL`, `DATABASE_URL`, `DEMO_MODE`. Only the first is present, misspelled.

**Action taken 2026-08-08.** A `.gitignore` was added covering `.env`, Python/Node build artefacts, and `*.db`. Verified with `git check-ignore -v .env`.

**Still outstanding.**
1. If this key was ever pasted into a commit, a chat, or a screen share, rotate it at <https://platform.deepseek.com>. Rotation is cheap; assume exposure.
2. Rename the variables to the spec-mandated names and expand `.env_example` to the full five-key contract.
3. `foodflow_clean_code_spec.md` §11 requires `security: secret_scan: required` — wire an actual scanner in P0, not just a checkbox.

---

## 2. External reality (verified August 2026)

### A-1 — ~~BLOCKER~~ → **CORRECTED (downgraded to Medium)** — model selection

> **Correction, 2026-08-08.** This finding originally asserted that `deepseek-chat` and
> `deepseek-reasoner` were permanently disabled on 2026-07-24 and would return errors. **That was
> wrong.** It rested on secondary blog sources rather than DeepSeek's own changelog — the
> `news0725` page I fetched turned out to be dated **July 2024**, not 2026, and reported the
> original JSON-output/function-calling release.
>
> A live probe of the API using this project's own key, run 2026-08-08, contradicts the claim:
>
> | Model | Result | `reasoning_content` |
> | --- | --- | --- |
> | `deepseek-chat` | **200 OK** | absent |
> | `deepseek-reasoner` | **200 OK** | present |
> | `deepseek-v4-flash` | 200 OK | **present** |
> | `deepseek-v4-flash` + `{"thinking":{"type":"disabled"}}` | 200 OK | absent |
>
> Both legacy aliases still resolve and respond. No migration is *forced*.

`foodflow_clean_code_spec.md` §6.4 requires a `DEEPSEEK_MODEL` env var but never names a model, so the choice has to be made somewhere. It is a choice, not a forced migration.

**Decision for this project:** `DEEPSEEK_MODEL=deepseek-v4-flash` with thinking explicitly disabled and `temperature=0` — chosen because it is the current generation and the legacy aliases are on a deprecation path, not because the aliases are dead. `deepseek-v4-pro` costs roughly 3.1× per token and is not required here.

**What the probe *did* confirm, and this is the load-bearing part:** `deepseek-v4-flash` runs with **thinking enabled by default** and returns `reasoning_content`; explicitly disabling it suppresses that field. See **D-5** and **R-1** — that constraint is now empirically verified rather than assumed, and it is the finding that actually matters.

**Method note.** The original error came from trusting SEO-oriented aggregator sites over primary sources, and from not checking the date on a page whose URL slug (`news0725`) was ambiguous between 2024 and 2026. `AGENTS_FoodFlow.md` §18 requires technical research to prioritise official and primary sources; a two-minute live probe would have caught this at the time, and did catch it later.

### A-2 — BLOCKER — LiteLLM supply chain compromise, and it is not an ADK extra

Google ADK reaches non-Gemini providers through LiteLLM (`from google.adk.models.lite_llm import LiteLlm`). Two facts change how it must be pinned:

1. **Versions 1.82.7 and 1.82.8, published to PyPI on 2026-03-24, were malicious.** A threat actor obtained the maintainer's PyPI credentials via a compromised Trivy binary in LiteLLM's CI pipeline and published releases containing a credential stealer — 1.82.7 via base64 payload inside `litellm/proxy/proxy_server.py`, 1.82.8 via a `litellm_init.pth` that fires on *every* Python interpreter start with no import required. It harvested SSH keys, environment variables, cloud credentials, and shell history. Pin **`litellm>=1.84`**. Given S-1, this is not theoretical for this repo.
2. **`litellm` is not among `google-adk`'s optional extras** (`a2a`, `db`, `eval`, `mcp`, `gcp`, …). It must be an explicit, separately pinned dependency — `AGENTS_FoodFlow.md` §5 requires all versions pinned in manifest or lock files.

The DeepSeek model string via LiteLLM is `deepseek/<model>`, with the key read from `DEEPSEEK_API_KEY`.

### A-3 — BLOCKER — ADK 2.x is a breaking-change platform

Current `google-adk` is **2.6.3 (released 2026-08-07)**, requiring **Python ≥3.10** — compatible with the spec's Python 3.12+. But ADK 2.0 replaced the hierarchical agent executor with a graph-based **Workflow Runtime**, and the following 1.x patterns — which dominate published tutorials and blog posts — are now broken:

- `BaseAgent` subclasses `BaseNode`; agents are evaluated as nodes in a workflow graph.
- Custom `_run_async_impl()` overrides are **bypassed**.
- `context.session.events.append()` is no longer supported; events must be yielded through framework channels.
- Broad `except` blocks now **mask failures from automatic retry** and break Human-in-the-Loop pausing.

That last point collides directly with `foodflow_clean_code_spec.md` §6.3 ("do not catch broad exceptions") — same rule, now enforced by the framework rather than by review.

**Action:** pin an exact ADK version in P0 (`google-adk==2.6.3` or the version verified by the P0 spike) and treat any 1.x-shaped example as untrusted.

### A-4 — RISK — DeepSeek tool-call parsing through LiteLLM is intermittently broken

`google/adk-python` issue **#5024** reports that with LiteLLM proxying DeepSeek-V3, the **first tool call consistently fails to parse** — the model returns raw text containing `<｜tool▁calls▁begin｜>` special tokens instead of a structured function call. The reporter notes it is intermittent ("sometimes it displays normally"). Reported against ADK 1.22.1 / LiteLLM 1.82.1; the issue is closed but the thread documents no workaround and no confirmed fix.

This matters more here than in a typical project: the design routes **14–16 tools** through exactly this path, twice per demo, in front of judges. On the API side the capability is fine — DeepSeek supports up to 128 tools and parallel function calls, and strict mode works in both thinking and non-thinking modes — so the fragility is in the ADK↔LiteLLM↔DeepSeek serialisation seam, not the model.

**Mitigation (P0 spike, before any Agent code is written):** stand up a throwaway script with ADK 2.6.x + `litellm>=1.84` + `deepseek-v4-flash`, register three trivial typed tools, and run 20 consecutive agent turns that require multi-tool use. Record the parse-failure rate. If it is non-zero, decide then between (a) a direct OpenAI-compatible `BaseLlm` adapter that bypasses LiteLLM, or (b) forcing single-tool-per-turn sequencing. Both are acceptable under `AGENTS_FoodFlow.md` §10 ("keep provider-specific code isolated in one adapter or model-factory module"); discovering the need on demo day is not.

---

## 3. Internal contradictions

### B-1 — CONFLICT — Two incompatible tool lists

`Requirement.md` §11 mandates 14 tools; `foodflow_clean_code_spec.md` §7.4 mandates 16 with different names. They are not a superset relation.

| Only in `Requirement.md` §11 | Only in `clean_code_spec` §7.4 |
| --- | --- |
| `list_community_options` | `list_candidate_communities` |
| `get_community_need_and_capacity` | `get_community_capacity` |
| `validate_capacity` | `validate_recipient_capacity` |
| `list_available_drivers` | `get_available_drivers` |
| `assign_driver` | `validate_storage_compatibility` |
| `return_remaining_inventory` | `validate_driver_capacity` |
| `create_rematch_order` | `reserve_inventory` |
| `update_driver_route` | `reserve_recipient_capacity` |
| | `release_remaining_inventory` |
| | `create_rematched_delivery` |

Compounding it, `Requirement.md` §11 says "do not create a large tool library beyond this journey" while the spec's list is the larger one. `AGENTS_FoodFlow.md` §4 forbids silently implementing "the most convenient version".

**Proposed resolution (confirm before P3).** Take `foodflow_clean_code_spec.md` §7.4 naming as authoritative — it is the more precise vocabulary (`recipient_capacity` vs bare `capacity`) and satisfies `clean_code_spec` §5.1's one-term-consistently rule. Add back the two Requirement-only tools that the journey genuinely needs and the spec omits: **`assign_driver`** and **`update_driver_route`**. Drop `list_available_drivers` in favour of `get_available_drivers`. Final count: **18 tools**. Then update *both* documents in the same change, as §4 requires.

### B-2 — CONFLICT — Six screens or seven

`Requirement.md` §2 says "build six visually strong screens" and folds the success state into Screen 6. `AGENTS_FoodFlow.md` §11 and `clean_code_spec` §8.1 both enumerate seven, adding "Final Success State".

**Proposed resolution:** six routes; "All 60 kg Rescued" is the terminal state of the Automatic Rematch screen, not a seventh route. This matches `Requirement.md` §8, which places the success state inside Screen 6. Low impact, but it changes the route table, so fix it before P5.

### B-3 — GAP — Required-reading paths do not exist

`AGENTS_FoodFlow.md` §3 instructs every contributor to read, before any code change:

| Referenced | Actual |
| --- | --- |
| `README.md` | Exists, but is a one-line stub (`# Woolworth_food_waste`) |
| `docs/clean_code_spec.md` | Does not exist — the file is `foodflow_clean_code_spec.md` at repo root |
| `docs/issues/pending-issues.md` (§14) | Does not exist |

An instruction file whose first mandatory step is a dead path will be ignored wholesale. Fix in P0.

### B-4 — Minor — Stack lists differ

`Requirement.md` §10 lists the stack without TanStack Query, React Hook Form, Zod, or shadcn/ui; `AGENTS_FoodFlow.md` §5 mandates all four. `AGENTS_FoodFlow.md` §4 makes itself authoritative for technology direction, so no real conflict — but `Requirement.md` §10 should be updated so the two read the same.

---

## 4. Demo-scenario assumptions

These are the findings most likely to break the pitch, because each one is a place where a *correctly implemented* system produces the wrong demo.

### C-1 — BLOCKER — No frozen demo clock

`validate_receiving_window` must compare against a current time. The scenario is pinned to a pickup window of 16:00–17:00 and a deadline of 19:00 NZ time. **If the demo is run at 10:00, every community is legitimately closed and the Agent correctly excludes all four.** The pitch dies, and the code is not at fault.

`DEMO_MODE` appears in `clean_code_spec` §6.4's env list with no defined semantics anywhere in the three documents.

Second-order problem: the JSON example in `Requirement.md` §4 hardcodes `+12:00`. That is correct NZST for August 2026 — but New Zealand moves to NZDT (`+13:00`) on **2026-09-27**. A hardcoded offset silently produces one-hour-wrong windows for any demo run after that date.

**Required:** a `Clock` port in the domain layer, injected everywhere. Under `DEMO_MODE=true` it returns a pinned instant (proposed: `2026-08-08T15:45:00+12:00`, fifteen minutes before the pickup window opens). Under `DEMO_MODE=false` it returns real time. Store timestamps as UTC internally and resolve NZ offsets through the `Pacific/Auckland` zone, never a literal `+12:00`.

### C-2 — BLOCKER — Nothing prevents the Agent from splitting the remaining 25 kg

`AGENTS_FoodFlow.md` §7 explicitly states DeepSeek "decides whether to **split** or rematch". Given 25 kg to place, with Community C offering 10 kg and Community D offering 30 kg, a well-reasoning model may allocate **10 kg → C + 15 kg → D**. That delivers all 60 kg, satisfies every hard constraint, and is arguably a *better* answer.

It also destroys the scripted beat that `Requirement.md` §8 and §16.3 depend on: "Community C excluded: only 10 kg capacity". The demo would show a two-stop split the narration does not describe, and test 3 would fail against a correct system.

**Required:** an explicit domain policy, enforced in Python and not merely hinted in the prompt — *prefer a single destination for the full remaining quantity; split only when no single feasible recipient can accept the entire remainder.* Under that policy D (30 kg ≥ 25 kg) wins outright and C is correctly excluded as insufficient **for a single-destination allocation**. Note the exclusion reason must be worded that way in the UI, or it is subtly untrue.

This belongs in the domain layer per `clean_code_spec` §9 ("duplicate allocation logic → centralize in one domain policy") and must never be a prompt-only rule, per §2.3 (the Agent must not make final product policy).

### C-3 — BLOCKER — Nothing prevents the Agent from re-selecting Community A

Sequence: A is reserved 60 kg → A accepts 35 kg → 25 kg returns to active inventory. If the capacity reservation is released naively, **A now shows 25 kg of free reserved capacity**, and A is the nearest candidate by definition — the driver is standing in its car park with zero travel time. A route-aware Agent may well re-select A, which then declines again, and the loop burns its step budget on stage.

Neither `Requirement.md` §8 nor `AGENTS_FoodFlow.md` §8.4 states that A is out of the running.

**Required, two rules:**
1. On partial acceptance, reduce the recipient's **declared capacity** to the accepted quantity — A's stated capacity becomes 35 kg, not "60 kg with 25 kg freed". The capacity report was wrong; correct it, don't just unreserve.
2. Exclude the recipient that triggered a partial acceptance from the candidate set for that donation's rematch. Record it as a typed exclusion reason (`RECIPIENT_DECLINED_THIS_DONATION`) so the UI can display it — which strengthens the pitch rather than hiding a hack.

### C-4 — GAP — The rematch delivery's pickup origin is undefined

At rematch time the driver is at Community A, physically holding 25 kg. `create_rematched_delivery` creating an ordinary `DeliveryOrder` implies origin = Woolworths Mount Eden, and the map will faithfully draw a pointless return trip to the store and back out to D.

`Requirement.md` §8 says "updated driver destination" and "new delivery order created for 25 kg", which implies a leg extension — but no document states it.

**Required:** the rematch order's origin is the driver's current location (Community A), the same driver is retained, and no second store pickup occurs. Model it as a `DeliveryOrder` with an explicit `origin` (a location, not implicitly the donating store) so both the first and rematched legs use one type. ETA for the new leg is computed from A → D, and must be checked against the 19:00 deadline.

### C-5 — GAP — Seed data is under-specified

`Requirement.md` §1 defines the four communities only by need, category acceptance, and capacity. The following are required by tools the same document mandates, and do not exist anywhere:

| Missing | Needed by |
| --- | --- |
| Coordinates for the store and all four communities | `calculate_route`, the Auckland map, all ETAs |
| Receiving windows for B, C, D (only A is implied "open") | `validate_receiving_window` |
| Driver seed: how many, vehicle capacity, start location | `get_available_drivers`, `validate_driver_capacity`, `assign_driver` |
| Community B's actual need profile | Screen 3 must show B's Need — it cannot be "vegetables" |
| Distance/speed basis for deterministic ETA | `calculate_route`, "route is simulated" labelling |
| A's declared total capacity and separately tracked remaining capacity | The whole allocation calculation — resolved by user decision 2026-08-08 as declared 60 / remaining 60 initially, then declared 35 / remaining 0 after partial acceptance |

**Note on drivers:** with one seeded driver, `validate_driver_capacity` and `get_available_drivers` are decorative and `Requirement.md` §10's "choose from feasible drivers" is untrue. Seed **three** drivers with differing vehicle capacities such that at least one is genuinely infeasible for 60 kg — this costs almost nothing and makes a mandated tool real.

Resolve all of this as a single committed seed fixture in P2. Per `AGENTS_FoodFlow.md` §2, the simulated nature of routes must be visibly labelled in the UI.

### C-6 — GAP — Storage compatibility is mandated but never demonstrated

The entire scenario is `ambient`, and Community B is excluded on **category**, not storage. So `validate_storage_compatibility` (`clean_code_spec` §7.4, §10.1) and `STORAGE_INCOMPATIBLE` (§6.3) will exist with zero coverage from the demo path.

**Decision:** implement and unit-test it, because §10.1 requires it, but spend no UI or seed effort on a chilled scenario. Document it as *implemented, not exercised by the pitch journey* — `AGENTS_FoodFlow.md` §19 requires exactly this kind of distinction.

### C-7 — GAP — Quantity integrity is a test name, not an invariant

`Requirement.md` §16.7 states "the remaining 25 kg is not duplicated" as a test. `AGENTS_FoodFlow.md` §8.4 calls quantity integrity "a blocker-level requirement". A test proves it for one path; an invariant proves it for all of them.

**Required:** express it as a checked invariant asserted at every state transition —

```
available_kg + reserved_kg + in_transit_kg + delivered_kg == donation_total_kg
```

— enforced in the application/transaction layer, with a violation raising a typed error rather than being caught by a test after the fact. `clean_code_spec` §8.4 additionally requires the UI to display "no duplicate quantity" as visible proof, so expose the four components through the API and render them as a stacked bar on the rematch screen. That turns a correctness requirement into a pitch asset.

---

## 5. Delivery risks

### D-1 — RISK — LLM latency versus a 2–3 minute pitch

Two Agent runs (initial match, rematch), each requiring a plan call, several tool round-trips, and an explanation call. At 2–5 s per round trip this plausibly consumes 30–90 s of the 120–180 s budget, most of it as dead air.

**Mitigations, all in scope:**
- `deepseek-v4-flash` in non-thinking mode, `temperature=0`.
- Stream the Agent's typed state events to the UI so waiting *looks like* the visible Agent states `Requirement.md` §12 already requires.
- Build a fixture-replay path. `clean_code_spec` §10.2 permits mocking DeepSeek; `AGENTS_FoodFlow.md` §10 requires deterministic fixtures so the journey is testable without a live key. That same path is the demo-day fallback if the venue network is hostile. Label it honestly — never present a replay as a live run.

### D-2 — RISK — The quality gate is heavy for a hackathon

`clean_code_spec` §11 marks all of Ruff, mypy, pytest, tsc, ESLint, Vitest, Playwright, agent evals, forbidden-import check, cycle check, secret scan, and E2E as `required`. That is achievable only if wired in P0 while the codebase is empty and kept deliberately narrow — retrofitting mypy strictness or an import-cycle check onto a finished MVP at hour 30 will not happen.

**Recommendation:** keep every gate `required` as written, but scope them tightly — one Playwright journey, six agent-eval cases, unit tests only on the domain policies. Wire the whole gate in P0 against a hello-world slice so it never has to be retrofitted.

### D-3 — RISK — Map tiles are an external network dependency

Leaflet/MapLibre default to remote tile servers. A hostile venue network breaks the map on the two screens that most need it, and `AGENTS_FoodFlow.md` §18 states the runtime must not depend on developer-local setup.

**Mitigation:** the markers, route polyline, and driver animation are our own geometry — only the basemap is remote. Ship a stylised static Auckland basemap (bundled raster tile subset for the Auckland bounding box, or a simple SVG coastline) as the default, with remote tiles as an optional enhancement. Decide in P6, not on demo day.

### D-4 — GAP — Animation transport left undecided

`Requirement.md` §15 defers WebSocket infrastructure "unless needed for the demo animation" — an explicitly unresolved condition. Leaving it open invites someone to build WebSockets at hour 25.

**Proposed resolution:** the Agent run returns a typed, ordered list of `AgentStateEvent`s; the frontend replays them with a timed reveal. No WebSocket, no SSE. This satisfies the staged-timeline requirement of `Requirement.md` §8 and the visible-states requirement of §12 with zero added infrastructure. Fix the decision in P4.

### D-5 — RISK — Thinking mode conflicts with the no-chain-of-thought rule

DeepSeek V4 supports thinking mode, and tool use is supported within it from V3.2 onward. But `AGENTS_FoodFlow.md` §7 and `clean_code_spec` §7.2/§7.3 prohibit persisting or displaying raw hidden reasoning, and §12 lists "hidden reasoning in logs or UI" as a blocker smell.

**Decision:** run non-thinking mode (also the faster choice per D-1). If thinking mode is ever enabled for quality reasons, `reasoning_content` must be stripped at the DeepSeek adapter boundary and must never reach the session store, logs, API responses, or fixtures.

---

## 6. What the demo scenario gets right

Recorded so the phase plan does not re-litigate settled points:

- **The arithmetic closes.** 35 kg (A) + 25 kg (D) = 60 kg. C's 10 kg is genuinely insufficient for a single-destination 25 kg allocation, and D's 30 kg genuinely suffices. No off-by-one.
- **The exclusion set is pedagogically complete.** Three distinct exclusion causes are demonstrated — unsupported category (B), insufficient capacity (C), and the declining recipient (A, once C-3 is implemented) — plus one selection. That is exactly enough to make the Need-vs-Capacity distinction of `Requirement.md` §9 land without padding.
- **`+12:00` is correct** for 2026-08-08 in Auckland (NZST). The C-1 concern is about durability past 2026-09-27, not about a present error.
- **Scope discipline is sound.** `Requirement.md` §15's deferral list is well-judged for a hackathon; nothing on it should be reinstated.
- **The layering is coherent.** The dependency direction in `AGENTS_FoodFlow.md` §6 and `clean_code_spec` §2.2 is identical and implementable at this size without ceremony.

---

## 7. Decisions required before coding

Each carries a proposed default. Implementation proceeds on the default unless overridden; overriding after the listed phase starts costs rework.

| # | Decision | Proposed default | Needed by |
| --- | --- | --- | --- |
| 1 | DeepSeek model | `deepseek-v4-flash`, non-thinking, `temperature=0` | P0 |
| 2 | Rotate the exposed API key | Yes — assume exposure | P0 |
| 3 | LiteLLM vs a direct OpenAI-compatible adapter | Decide from the P0 spike's measured parse-failure rate | P0 |
| 4 | Tool list reconciliation | `clean_code_spec` §7.4 naming + `assign_driver` + `update_driver_route` = 18 tools | P3 |
| 5 | Screen count | Six routes; success state is terminal state of Screen 6 | P5 |
| 6 | Allocation strategy | Single-destination preferred; split only if no single recipient fits | P1 |
| 7 | Declining recipient | Capacity corrected to accepted amount **and** excluded from this donation's rematch | P1 |
| 8 | Rematch origin | Driver's current location; same driver; no return to store | P1 |
| 9 | Demo clock | `Clock` port; `DEMO_MODE=true` pins `2026-08-08T15:45+12:00`; `Pacific/Auckland` zone, never a literal offset | P1 |
| 10 | Driver seed | Three drivers, differing vehicle capacities, at least one infeasible for 60 kg | P2 |
| 11 | Animation transport | Typed event list + frontend timed replay; no WebSocket/SSE | P4 |
| 12 | Basemap | Bundled static Auckland basemap default; remote tiles optional | P6 |

---

## 8. Sources

- [google/adk-python issue #5024 — LiteLLM + DeepSeek-V3 multi-tool calling parse failure](https://github.com/google/adk-python/issues/5024)
- [google-adk on PyPI (2.6.3, 2026-08-07)](https://pypi.org/project/google-adk/)
- [Welcome to ADK 2.0 — breaking changes and Workflow Runtime](https://adk.dev/2.0/)
- [ADK — LiteLLM model integration](https://adk.dev/agents/models/litellm/)
- [ADK — Runtime Config (`max_llm_calls`)](https://adk.dev/runtime/runconfig/)
- [LiteLLM — DeepSeek provider](https://docs.litellm.ai/docs/providers/deepseek)
- [LiteLLM — Security update: suspected supply chain incident](https://docs.litellm.ai/blog/security-update-march-2026)
- [BerriAI/litellm issue #24518 — compromised PyPI releases, full timeline](https://github.com/BerriAI/litellm/issues/24518)
- [Bitsight — Supply chain compromise in LiteLLM 1.82.7 / 1.82.8](https://www.bitsight.com/blog/litellm-versions-1-82-7-1-82-8-supply-chain-compromise)
- [DeepSeek API Docs — V4 preview / GA release](https://api-docs.deepseek.com/news/news260424/)
- [DeepSeek API Docs — Tool Calls](https://api-docs.deepseek.com/guides/tool_calls/)
- [DeepSeek — chat/reasoner retirement and V4 migration, 2026-07-24](https://deepseekv4pro.com/guides/deepseek-chat-reasoner-retirement-date)
