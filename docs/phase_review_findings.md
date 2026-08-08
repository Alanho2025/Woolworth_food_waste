# Phase Plan Review — Three-Pass Findings

- **Date:** 2026-08-08
- **Subject under review:** `docs/implementation_phases.md` v1.0 and `docs/assumption_audit.md`
- **Codebase state at review:** **Greenfield.** Four tracked files, all Markdown. Zero source files (`*.py`, `*.ts`, `*.tsx`), no manifest, no lock file, no CI. Every statement about "existing code" in any planning document is therefore a statement about *intent*, and `AGENTS_FoodFlow.md` §2 requires it to be labelled **planned**.
- **Outcome:** 34 findings. **9 of them are defects in the phase plan itself**, including two that would have produced a broken demo and one that is architecturally impossible as specified.

## Method

| Pass | Lens | What it looked for |
| --- | --- | --- |
| **1** | Per-phase internal audit | Every technical claim the plan makes, re-verified against primary sources. The plan asserted API shapes, config fields, and library behaviour; each was checked rather than assumed. |
| **2** | Cross-phase alignment | Dependency direction between phases, entry/exit criteria consistency, and work that falls in the seam between two phases and is therefore owned by neither. |
| **3** | Traceability & decision extraction | Every numbered test in `Requirement.md` §16 and every completion criterion in §17 mapped to an owning phase task. Residue that maps to nothing is a gap; residue that maps to two conflicting places is a contradiction. |

Findings are graded by the taxonomy requested:

`CONTRA` contradiction · `ASSUM` unsupported assumption · `GAP` gap · `MISSREQ` missing requirement · `AMBIG` ambiguity · `WEAK` weak reasoning · `HUMAN` requires a human answer

---

## Summary

| ID | Type | Finding | Origin | Severity |
| --- | --- | --- | --- | --- |
| R-1 | **CONTRA** | Thinking mode + tools **requires** retaining `reasoning_content`, which the spec forbids | Spec | **Blocker** |
| R-2 | **CONTRA** | Plan says "stream events" and "return the event list at the end" — mutually exclusive | Plan | **Blocker** |
| R-3 | **CONTRA** | Plan claims P5 runs parallel to P3, but P5's entry criterion is a P4 output | Plan | High |
| R-4 | **ASSUM** | `deepseek-v4-flash` defaults to thinking **enabled**; plan assumed non-thinking was free | Plan | **Blocker** |
| R-5 | **ASSUM** | ADK Python `RunConfig` has **no** per-tool or wall-clock timeout; plan claimed both | Plan | High |
| R-6 | **ASSUM** | Audit said litellm is not an ADK extra; it is pulled in by `eval` and `extensions` | Audit | High |
| R-7 | **ASSUM** | Bulk-downloading OSM tiles for offline use is **prohibited** by the tile usage policy | Plan | High |
| R-8 | **ASSUM** | `extra_body` passthrough via ADK's `LiteLlm` wrapper is unverified | Plan | High |
| R-9 | **CONTRA** | `DEMO_MODE` is one boolean driving two unrelated flows — violates `clean_code_spec` §5.2 | Plan | Medium |
| R-10 | **CONTRA** | Audit criticism of the spec's transaction step 6 loses the audit trail for failures | Spec | Medium |
| R-11 | **GAP** | No task builds the E2E harness (two servers + seeded DB + teardown) | Plan | High |
| R-12 | **GAP** | Dashboard is built in P5 but must reflect state produced in P7; nothing revisits it | Plan | High |
| R-13 | **GAP** | Agent-eval gate is `required` in P0 but has nothing to run until P3 | Plan | Low |
| R-14 | **GAP** | No stated threshold for abandoning live model calls in favour of replay | Plan | Medium |
| R-15 | **GAP** | "Backend starts" is a `Requirement.md` §17 criterion owned by no exit check | Plan | Low |
| R-16 | **GAP** | Spike script deleted at P0 end, destroying the evidence P0-7's decision rests on | Plan | Low |
| R-17 | **MISSREQ** | Quantity type never specified — float kg makes the integrity invariant undecidable | Plan | **Blocker** |
| R-18 | **MISSREQ** | ETA must be computed for *excluded* candidates too; short-circuit validation blanks the UI | Spec | High |
| R-19 | **MISSREQ** | Route polyline geometry undefined; straight lines across the Waitematā look wrong | Spec | Medium |
| R-20 | **MISSREQ** | OSM attribution "© OpenStreetMap contributors" is mandatory and appears nowhere | Plan | Medium |
| R-21 | **MISSREQ** | Dashboard "kilograms rescued" has no defined data source | Spec | Medium |
| R-22 | **MISSREQ** | No remediation step for the `litellm_init.pth` backdoor artefact | Plan | Medium |
| R-23 | **AMBIG** | Driver animation timing: auto-play with compression, or manual advance? | Spec | High |
| R-24 | **AMBIG** | Does rematch fire automatically on confirm, or need a second click? | Spec | High |
| R-25 | **RESOLVED** | A's 60 kg is declared total capacity; remaining capacity is tracked separately | User decision 2026-08-08 | High |
| R-26 | **AMBIG** | Dashboard's "urgent donation card" implies pre-existing state the seed doesn't define | Spec | Medium |
| R-27 | **AMBIG** | Community A's displayed Need after declining is unspecified | Spec | Low |
| R-28 | **WEAK** | "10/10 live runs" as an exit criterion is statistically near-meaningless | Plan | Medium |
| R-29 | **WEAK** | Audit treated issue #5024 as an ADK↔LiteLLM seam defect without considering thinking mode | Audit | Medium |
| R-30 | **WEAK** | Pinning `google-adk==2.6.3` exactly, on a package shipping releases weekly | Plan | Low |
| R-31 | **WEAK** | Deadline validation is never meaningfully exercised by the pinned-clock demo | Plan | Low |
| R-32 | **HUMAN** | Deadline, team size, and available hours are unknown — plan feasibility is unassessed | — | **Blocker** |
| R-33 | **HUMAN** | Do the competition rules require a live model call, or is replay acceptable? | — | High |
| R-34 | **HUMAN** | Demo time of day vs DeepSeek surge-pricing windows and venue network | — | Medium |

---

## 1. Contradictions

### R-1 — Thinking mode and the no-chain-of-thought rule are architecturally incompatible **[Blocker]**

Three documents prohibit retaining raw reasoning: `AGENTS_FoodFlow.md` §7 ("persist hidden chain-of-thought" is forbidden), `clean_code_spec` §7.2 (Agent state must not store raw hidden reasoning), and §12, which lists "hidden reasoning in logs or UI" as a **blocker-level** smell.

DeepSeek's own documentation states that in thinking mode, **"for requests carrying the `tools` parameter, the `reasoning_content` must be fully passed back to the API in all subsequent requests"** — omitting it returns a 400. Real projects are hitting this in production (`anomalyco/opencode` #24130).

So thinking mode plus tools **forces** the application to carry reasoning through its conversation state. That is not a preference to be traded off; it is a direct collision with a blocker-level rule.

**Consequence:** non-thinking mode is not the *recommended* option, it is the **only spec-compliant** one. This must be recorded as a hard constraint rather than a performance tuning choice, because someone will otherwise enable thinking mode later to improve decision quality and silently violate three rules at once.

### R-2 — The plan both streams and batches the agent event list **[Blocker, plan defect]**

Two statements in the plan cannot both hold:

- **P4-3:** "Serve the agent run as a typed ordered `AgentStateEvent` list… the frontend replays the event list with a timed reveal. No WebSocket, no SSE."
- **D-1 mitigation:** "Stream the Agent's typed state events to the UI so waiting *looks like* the Agent working."

If the list is only returned when the run completes, nothing can be streamed. The user watches a spinner for the **entire** 30–90 s agent run, and only then sees a fast, pre-baked replay. That is strictly worse than doing nothing: it concentrates all the dead air into one block *and* makes the visible states arrive after the decision they were supposed to explain.

The batch design also quietly falsifies the pitch. `Requirement.md` §12's eleven visible states exist to show the Agent thinking. Replaying them from a completed run shows an animation, not a system.

**Resolution:** the run starts asynchronously and returns a run ID; the frontend polls `GET /agent-runs/{id}` at ~500 ms and renders events as they land. This still honours `Requirement.md` §15's WebSocket deferral — polling is not WebSocket infrastructure — while actually hiding the latency. Cost is one endpoint and a `useQuery` refetch interval.

### R-3 — P5 cannot run parallel to P3 as the plan claims **[plan defect]**

The phase map states: *"P5 may start in parallel with P3 once P4's contracts are frozen (see P4-6)."* But P5's entry criterion is E4.2, E4.2 is a P4 exit criterion, and P4's own entry criterion is "P3 exit criteria pass". The parallelism is self-cancelling — P5 cannot start until P3 is finished.

This matters because P3 is the longest and riskiest phase, and serialising all frontend work behind it wastes the one genuine opportunity for concurrent work.

**Resolution:** move contract freezing earlier. The Pydantic contracts already exist at P1-1; the API surface can be declared from them at the end of P2 as a contract-first artefact, before any agent code is written. Frontend then unblocks after P2.

### R-9 — `DEMO_MODE` is one flag driving two unrelated flows

`clean_code_spec` §5.2: *"Boolean flags MUST NOT make one function perform unrelated flows."*

The plan loads `DEMO_MODE` with two unrelated jobs: pinning the clock (P1-2) and selecting fixture replay over live model calls (P3-13, P8-2). These are independent axes — a live model run against a pinned clock is exactly what rehearsal needs, and the single flag makes that combination unreachable.

**Resolution:** two settings. `DEMO_MODE=true|false` (pinned clock + seeded world) and `AGENT_TRANSPORT=live|replay`. Four combinations, all meaningful.

### R-10 — Writing the audit event inside the transaction destroys the failure audit

`clean_code_spec` §6.2 specifies the allocation transaction as six steps ending in *"create audit event"*, and states that if any step fails the transaction **must roll back**.

Taken literally, a failed allocation rolls back its own audit record. The system then has no durable evidence of attempts that were rejected — which is precisely the evidence `AGENTS_FoodFlow.md` §14 demands when diagnosing correctness issues, and precisely what the Agent-decision audit trail exists for.

**Resolution (confirmed by the implementation-plan default at P2):** success audit inside the transaction, failure audit written on a separate connection after rollback. `clean_code_spec` §6.2 was updated in the same change so the durable failure evidence survives without retaining partial product writes.

---

## 2. Unsupported assumptions

These are claims the plan asserted without evidence. Each was checked; **four of the five were wrong.**

### R-4 — `deepseek-v4-flash` runs with thinking **enabled by default** **[Blocker, plan defect]**

The plan said "use non-thinking mode" as though it were the default. It is not: **DeepSeek-V4-Flash defaults to thinking enabled.** Disabling it requires explicitly passing `extra_body={"thinking": {"type": "disabled"}}` on every request.

Three consequences follow from getting this wrong, and the plan would have shipped all three:

1. Every call is slower — directly worsening the 2–3 minute budget of D-1.
2. `reasoning_content` is returned, triggering the R-1 blocker.
3. Thinking-by-default is independently reported to cause **JSON parse failures** (`Graphify-Labs/graphify` #1621 attributes an observed parse failure to exactly this).

**Empirically confirmed 2026-08-08** by a live probe with the project's own key: `deepseek-v4-flash` returned `reasoning_content`; the same call with `{"thinking": {"type": "disabled"}}` did not. This finding stands on measurement, not inference.

The legacy aliases behave as the mode shorthand — `deepseek-chat` returned no `reasoning_content`, `deepseek-reasoner` did — and, contrary to audit finding A-1, **both still resolve**. See the correction recorded at A-1; the retirement claim came from secondary sources and was wrong. It does not affect this finding, which is the one that actually constrains the build.

**Implementation detail:** the parameter travels at the **top level** of the request body. `extra_body` is an OpenAI-SDK convenience that merges its contents into the top level — there is no nested `extra_body` key on the wire.

### R-5 — ADK Python's `RunConfig` has no timeout fields **[plan defect]**

P3-6 instructed: *"Bound it with `RunConfig.max_llm_calls`… a wall-clock timeout, a per-tool timeout."*

Verified against the ADK runtime configuration reference: `RunConfig` exposes `max_llm_calls` (default **500**), `streaming_mode`, `speech_config`, `response_modalities`, `save_live_blob`, `tool_thread_pool_config`, and `custom_metadata`. **There is no per-tool timeout and no wall-clock timeout.**

The `ToolCallTimeout` and `MaxTurns` fields that informed the original claim come from **`adk-golang`, a third-party Go port** — not the Python SDK this project uses. That is a citation error in the audit's research, and it produced an instruction that cannot be followed.

This matters because timeouts are *mandatory*, not optional: `clean_code_spec` §7.1 requires the loop to have "a timeout", and §7.4 requires a timeout on every tool that performs I/O. Since the framework does not supply them, they must be **built**: `asyncio.wait_for` around the runner invocation for the wall clock, and an explicit timeout inside each I/O-performing tool. This is now real work that the plan had accounted for as configuration.

Note also that `max_llm_calls=500` is a wildly permissive default for this journey — a runaway loop would make 500 DeepSeek calls before stopping.

### R-6 — litellm *is* an ADK dependency, via extras **[audit defect]**

The audit stated litellm "is not among `google-adk`'s optional extras". That reading came from the extras *names* list. In fact `google-adk[eval]` and `google-adk[extensions]` both depend on litellm — confirmed by `google/adk-python` #4981, where PyPI's quarantine of litellm broke installation of both extras outright, and by ADK's own security notice telling users of the `eval` or `extensions` extras to upgrade.

This is not academic. **`clean_code_spec` §11 makes `agent: core_eval: required`**, and §10.1 mandates six agent-eval cases. The eval extra is therefore on the critical path, which puts litellm on the critical path *even if P0-7 decides to bypass LiteLLM for model calls*. The dependency cannot be avoided by writing a direct adapter; it can only be pinned and monitored.

Current state: PyPI quarantined the entire package for a period; it has since been restored, and **litellm 1.95.0 (2026-08-02)** is current. Safe versions are ≤1.82.6 or ≥1.83.0; ADK's guidance is ≥1.84.

### R-7 — Bulk-downloading OSM tiles for offline bundling is prohibited **[plan defect]**

P6-8 proposed shipping "a raster tile subset for the Auckland bounding box". The OSM Foundation Tile Usage Policy explicitly prohibits this: **offline use of `tile.openstreetmap.org` is not permitted**, and features that prefetch or bulk-download areas are named as prohibited uses.

The plan's mitigation for D-3 was therefore a licence violation, recommended in a document whose companion rules require official sources and correct attribution.

**Legitimate routes to the same outcome:** generate tiles yourself from an OSM extract into a single MBTiles file (OpenMapTiles or equivalent) and serve it locally; use a provider whose terms permit offline caching; or draw a stylised SVG basemap from an Auckland coastline extract, which for this pitch is probably sufficient and is the cheapest option by a wide margin. Vector tiles are the better technical fit if a real basemap is wanted.

### R-8 — `extra_body` passthrough through ADK's `LiteLlm` wrapper is unverified **[plan defect]**

R-4 establishes that `extra_body={"thinking":{"type":"disabled"}}` must reach DeepSeek on every request. The path is `ADK LlmAgent → LiteLlm wrapper → litellm.completion → DeepSeek`. Whether ADK's wrapper forwards arbitrary kwargs through that chain is **not documented**, and LiteLLM has a history of `extra_body` passthrough bugs (#20982, #18039, #4769 — including one where the parameter was accepted and documented but never actually sent).

If passthrough fails silently, the system runs in thinking mode while believing it is not, and R-1's blocker is live in production with no visible symptom other than latency.

**This must be an explicit, asserted step in the P0 spike:** make a call, and assert on the response that `reasoning_content` is absent. Do not infer it from the absence of an error.

---

## 3. Gaps

### R-11 — Nobody builds the E2E harness **[High]**

P8-1 requires a Playwright test spanning Donate → … → Completed Delivery. That needs a FastAPI process, a Next.js process, a seeded database, deterministic agent behaviour, and teardown — orchestrated. P0-8 wires Playwright against a hello-world page; P8-1 assumes a working harness appears. No task builds one.

This is the classic phase-seam gap: P0 owns "Playwright runs", P8 owns "the journey passes", and nobody owns "the two servers and the database come up together reproducibly". It typically surfaces at the worst possible time.

### R-12 — The Dashboard is built in P5 but shows data produced in P7 **[High]**

`Requirement.md` §3 requires the Dashboard to show "one alert showing a community capacity change" and "food currently in transit". Both are states created by the partial acceptance in **P7**. The Dashboard is built and closed in **P5**, and no later task revisits it.

Underneath sits an unanswered design question: is the Dashboard live throughout the demo — so a judge can return to it and see the journey reflected — or is it only the opening slide? The first is far more convincing and requires a refetch strategy; the second is cheaper. Nothing decides.

### R-13 — The agent-eval gate has nothing to run until P3

P0-8 wires the complete `clean_code_spec` §11 gate, which includes `agent: core_eval: required`. At P0 there is no agent. Either the gate stage is a placeholder that must be filled at P3 — and nothing says so, meaning it will stay green and empty — or P0-8 cannot honestly claim to have wired the full gate.

### R-14 — No threshold for abandoning live model calls **[Medium]**

E3.7 says "10 consecutive live runs all select A then D" and instructs reporting the actual number. It never says what number is *acceptable*, or what happens at 8/10. Without a pre-committed bar, this decision gets made under pressure the night before the demo, which is when people talk themselves into optimistic readings. See also R-28.

### R-15 — "Backend starts" is owned by no exit criterion

`Requirement.md` §17 lists "the backend starts" as a completion criterion. It is implied by several exit checks but asserted by none. Trivial to fix, and exactly the kind of item that a completion checklist is for.

### R-16 — The spike is deleted along with its evidence

P0-6 says the spike is "throwaway, deleted at phase end", while P0-7's transport decision — one of the most consequential in the project — rests entirely on the numbers it produced. If DeepSeek or LiteLLM behaviour shifts mid-project, the measurement cannot be reproduced.

Keep it as a committed test marked skip-by-default. The cost is zero and it converts an anecdote into a repeatable check.

---

## 4. Missing requirements

### R-17 — The quantity type is never specified **[Blocker]**

The whole product rests on `available + reserved + in_transit + delivered == 60`. **No document states whether quantities are `int`, `float`, or `Decimal`.**

With IEEE-754 floats this invariant is not reliably decidable — the natural implementation of "return the remainder to inventory" involves subtraction, and repeated float arithmetic across the reserve/release/re-reserve cycle can leave a residue that makes an exactly-correct system report a violation, or an incorrect one pass. `AGENTS_FoodFlow.md` §8.4 calls quantity integrity blocker-level; leaving its numeric type unstated undermines the single most important guarantee in the product.

E7.1 in the plan says "no rounding drift" as an exit criterion without ever mandating a type that would prevent it — asserting an outcome while omitting its cause.

**Resolution:** integer kilograms throughout. The demo uses 60/35/25/30/10 — all integers. If fractional quantities are ever needed, `Decimal`, never `float`. Enforce at the Pydantic contract layer in P1-1 so it cannot drift.

### R-18 — Excluded candidates still need computed ETAs **[High]**

`Requirement.md` §5 requires **each** of the four community cards to display need, remaining capacity, category compatibility, opening status, **estimated arrival**, and final status. So Community B — excluded on category — must still show an ETA.

The natural implementation short-circuits: check category, fail, return an exclusion, never compute a route. B's card then renders with a blank ETA, and the comparison table that is the centrepiece of the most important pitch screen has holes in exactly the rows meant to demonstrate rigour.

**Requirement:** the fact-gathering pass computes *all* displayable facts for *all* candidates; eligibility is then applied as a **label over a complete fact set**, never as an early return. This shapes the P3-2/P3-3 tool contracts and needs stating before they are written.

### R-19 — Route geometry is undefined **[Medium]**

P1-10 specifies Haversine distance × a fixed speed. That yields a *number*. `Requirement.md` §6 additionally requires a "route line on Auckland map" that "must look credible".

A straight geodesic between Mount Eden and a community across the Waitematā Harbour will render as a line through water and over volcanic cones. To an Auckland judge that reads as broken, and it undercuts the honest "simulated" label by looking careless rather than deliberate.

**Requirement:** seed a hand-traced plausible polyline for each route pair actually drawn — Store→A, A→D, plus any candidate route shown on Screen 3. That is a handful of coordinate lists, cheap to produce, and far more credible than a straight line. Distance for ETA can then be the polyline length, which is also more honest.

### R-20 — OSM attribution is mandatory and appears nowhere **[Medium]**

OSM data is ODbL-licensed and attribution — "© OpenStreetMap contributors" — is **required**, whichever tile route R-7 resolves to. No task in any phase places it. It is a visible, non-negotiable UI element on two screens.

### R-21 — "Kilograms rescued" has no data source **[Medium]**

`Requirement.md` §3 requires an impact summary "such as kilograms rescued" on the opening screen. If it counts only the current donation it reads **0 kg** at the moment the pitch begins — the worst possible number on the opening slide. If it is cumulative it needs seeded historical deliveries, which P2-4 does not define. Nothing anywhere decides. See R-26, which is the same problem in a different widget.

### R-22 — No remediation step for the litellm backdoor artefact **[Medium]**

LiteLLM's incident guidance instructs users to inspect `site-packages` for **`litellm_init.pth`** and remove it if present — the 1.82.8 payload persisted via that file and executed on *every* Python interpreter start, with no import required. Any developer machine that touched the bad versions in the ~40-minute window is affected regardless of what is pinned now.

Given this repository shipped a live API key in an un-ignored `.env` (audit S-1), the two findings compound. A check belongs in P0 alongside the key rotation.

---

## 5. Ambiguities

### R-23 — Driver animation timing is undefined **[High]**

Screen 4 requires a "moving driver marker or simulated route progress". A real Mount Eden → community drive is 15–25 minutes; the entire demo budget is 2–3 minutes. So the animation must be time-compressed — but no document states the compression factor, whether it auto-plays, or what advances it.

`Requirement.md` §6 also lists an "Arrived at Recipient" button, which implies **manual** advance — in which case the progress animation is decorative and can be a short scripted loop. If instead it auto-plays, someone must pick a factor and the button becomes a skip control. These are materially different builds; the choice is a human one (see Q4).

### R-24 — Does the rematch fire automatically? **[High]**

Screen 5's primary button is "Confirm and Rematch Remaining Food" — one action, two effects. `AGENTS_FoodFlow.md` §21 requires that "no routine human approval is introduced".

So: on click, does the Agent immediately run and the UI transition into a live Screen 6? Or does Screen 6 load and wait for another click to start? Only the first is consistent with the autonomy claim the pitch makes, and it is the more impressive demo — but nothing states it, and the second is what a developer building screen-by-screen will naturally produce.

### R-25 — Is Community A's 60 kg total or remaining capacity? **[High, resolved]**

Raised as audit C-5 because it is not a data-entry detail: it changes the meaning of every capacity number on Screen 3, the arithmetic of the reservation in P2-3, and the semantics of the correction in P1-6. **Resolved by user decision on 2026-08-08:** 60 kg is A's declared total capacity, while remaining capacity is stored separately. A begins at declared 60 / remaining 60, reaches remaining 0 after the reservation, and after accepting 35 kg its corrected state is declared 35 / remaining 0.

### R-26 — The Dashboard implies pre-existing activity the seed doesn't define **[Medium]**

`Requirement.md` §3 requires "one highlighted urgent donation card", "one active Agent decision card", and "one active delivery card" — all before the demo's donation is created. The seed (P2-4/P2-5) defines only communities and drivers, so at demo start these cards are empty and the Dashboard reads as a blank reporting page, which §3 explicitly says it must not.

The obvious fix — seed a second in-flight donation — interacts badly with R-17's integrity display and the "All 60 kg Rescued" arithmetic if not carefully scoped. Needs a decision, not a default.

### R-27 — Community A's displayed Need after declining **[Low]**

A is seeded as "urgently needs vegetables". After it accepts only 35 kg, is its Need still "High"? Screen 6 and the Dashboard may show A concurrently with the rematch, and an unchanged "urgent need" beside "declined 25 kg" invites a question the presenter cannot answer cleanly.

---

## 6. Weak reasoning

### R-28 — "10 consecutive live runs" is close to statistically meaningless

E3.7 proposes 10 runs as the confidence bar for demo safety. If the true per-run failure rate is 10%, a 10-run clean streak happens **35%** of the time. Passing that check would license real confidence in a system that fails roughly one demo in ten — and there is only one demo.

The reasoning is weak in a second way: it measures the wrong thing. A failure that is *visible and recovers* is survivable on stage; one that hangs is not. Counting outcomes ignores that distinction.

**Better:** run 30, record the failure count **and** the p95 wall-clock time, and classify each failure as recovered / visible-error / hung. Pre-commit the decision rule before seeing the data (see R-14, Q5).

### R-29 — Issue #5024 was analysed without considering thinking mode

The audit attributed the DeepSeek tool-call parse failures (A-4) to the "ADK↔LiteLLM↔DeepSeek serialisation seam". That may be right, but R-4 supplies a competing hypothesis the audit never considered: **thinking mode is on by default**, and thinking-by-default is independently reported to cause JSON parse failures.

The intermittency reported in #5024 ("sometimes it displays normally") fits a thinking-mode explanation at least as well as a serialisation one.

This changes the spike design materially. The P0 spike must run **both arms** — thinking explicitly disabled, and default configuration — because if the failures vanish with thinking disabled, the entire "bypass LiteLLM" contingency is unnecessary work and the audit's A-4 risk rating drops sharply.

### R-30 — Pinning `google-adk==2.6.3` exactly

ADK shipped 2.6.2 on 2026-08-04 and 2.6.3 on 2026-08-07 — three days apart. Pinning an exact patch on a package moving that fast means bug fixes require a deliberate plan change, on a framework that had a major breaking release this year and whose 2.x behaviour the project is still discovering.

`AGENTS_FoodFlow.md` §5 requires versions pinned in *manifest or lock files* — which a compatible range plus a lock file satisfies. Prefer `google-adk>=2.6.3,<2.7` in the manifest with the exact version captured in the lock, giving reproducibility without freezing out patches.

### R-31 — Deadline validation is never meaningfully exercised

With the clock pinned at 15:45 and the whole journey compressed into three minutes, every check against the 19:00 deadline passes by a margin of hours. `validate_receiving_window` and the deadline logic will be implemented, unit-tested, and never once observed doing real work in the demo.

That is an acceptable outcome, but it should be *stated* — otherwise someone will invest UI effort in deadline pressure that the scenario never generates, or, worse, conclude the demo proves the logic works. Per `AGENTS_FoodFlow.md` §19 it belongs in the README status table as *implemented, unit-tested, not exercised by the pitch journey* — the same treatment as storage compatibility (audit C-6).

---

## 7. Questions requiring human answers

Ordered by how much downstream work each one changes.

### Q1 (R-32) — What is the deadline, and how many people are building this? **[Blocker]**

Nothing in the repository states the hackathon date, the hours remaining, or the team size. **The plan's feasibility is completely unassessed**, and it is not a small plan: nine phases, a fifteen-stage quality gate, Playwright, six agent-eval cases, and a full six-screen polished frontend.

Rough sizing: as specified, this is on the order of **60–100 focused engineering hours**. For four people over a weekend that is tight but real. For one person over 48 hours it is not achievable, and the correct response is to cut scope deliberately now — a shorter, working journey beats nine well-planned phases of which six get finished.

I cannot make that call, and every other estimate in this plan is conditional on it.

### Q2 (R-33) — Do the rules require a live model call? **[High]**

P3-13's fixture-replay path is both a testing requirement and the demo-day network fallback. Some competitions require a genuinely live inference call; others only care about the demonstrated journey. If live is mandatory, the R-28 reliability work and the D-1 latency budget become critical-path rather than contingency, and P8 needs materially more time.

### Q3 (R-26, R-21) — Should the demo world contain pre-existing activity? **[Resolved]**

Yes. Seed 2–3 *completed* historical deliveries (giving a credible rescued total and a populated map) plus one *in-flight* delivery belonging to a different donation, clearly separated from the demo donation so the 60 kg integrity display stays unambiguous.

### Q4 (R-23) — Auto-playing driver animation, or manual advance?

**Recommendation:** manual advance via the "Arrived at Recipient" button, with a short looping progress animation. It is less build, it keeps the presenter in control of pacing — which matters a great deal in a 3-minute pitch — and it matches the button `Requirement.md` §6 already specifies.

### Q5 (R-14, R-28) — What is the pre-committed bar for running the demo live?

**Recommendation, to be fixed before P3 begins:** 30 runs; **zero hung failures** and **p95 under 20 s** to run live. Anything else demos on replay with the live path shown afterwards as a secondary, honestly labelled.

### Q6 (R-10) — Should failed allocation attempts be audited durably? **[Resolved]**

Yes — success audit inside the successful transaction, failure audit outside it after rollback. The same-change `clean_code_spec` §6.2 update records this transaction boundary explicitly.

### Q7 (R-34) — What time of day is the demo, and what is the venue network?

DeepSeek's V4 surge pricing doubles rates during Beijing 09:00–12:00 and 14:00–18:00 — which in NZST is **13:00–16:00 and 18:00–22:00**, squarely covering a typical afternoon or evening judging slot. It was reported as not yet active as of 2026-08-02, but it may activate. The larger concern is not cost but latency: DeepSeek does not enforce hard rate limits and instead serves every request it can, so peak load degrades into **slowness rather than errors** — the failure mode that most directly threatens the 2–3 minute budget.

The venue network answer also determines how much of R-7's basemap work is genuinely required.

---

## 8. Traceability

Every numbered test in `Requirement.md` §16 now maps to an owning task. This mapping did not previously exist in written form, which is how R-11 and R-15 went unnoticed.

| `Requirement.md` §16 test | Owning tasks |
| --- | --- |
| 1. Donation submission produces valid JSON | P4-5, P5-8 |
| 2. Community B excluded — unsupported category | P1-11, P3-14, P6-3 |
| 3. Community C excluded — insufficient capacity | P1-5, P1-11, P6-3 |
| 4. Community A selected for the first 60 kg | P3-14, E3.7 |
| 5. Driver and route created | P2-5, P3-4, P6-6 |
| 6. Partial acceptance: 35 accepted, 25 remaining | P1-9, P7-1 |
| 7. The remaining 25 kg is not duplicated | P1-8, P1-17*, E7.4 |
| 8. Community D selected for the rematch | P1-5, P1-6, P3-14 |
| 9. Driver route updates | P1-7, P7-4 |
| 10. Final delivered quantity equals 60 kg | P8-1, E8.4 |

\* new task added in response to R-17 (integer quantity type).

Two `Requirement.md` §17 completion criteria had no owner before this review: **"the backend starts"** (R-15) and, indirectly, the E2E harness that proves several of the others (R-11).

---

## 9. What survived all three passes

Recorded so these are not re-examined a fourth time:

- **The demo arithmetic.** 35 + 25 = 60; C's 10 kg is genuinely insufficient under a single-destination policy; D's 30 kg genuinely suffices. Checked again against the exclusion ordering — still sound.
- **The layering.** The dependency direction in `AGENTS_FoodFlow.md` §6 and `clean_code_spec` §2.2 is identical, implementable at this size, and the forbidden-import test makes it enforceable rather than aspirational.
- **The domain-first phase ordering.** Putting every allocation rule in pure Python before any LLM touches the system is what makes C-2 and C-3 fixable as policy rather than prompt engineering. Three passes found no reason to reorder.
- **The audit's demo-scenario findings (C-1 through C-7).** Re-examined; all still hold, and R-17 strengthens C-7 rather than replacing it.
- **Scope discipline.** `Requirement.md` §15's deferral list remains well-judged. Nothing found in three passes argues for reinstating any of it.

---

## Sources

- [ADK — Runtime Config (`max_llm_calls`, field list)](https://adk.dev/runtime/runconfig/)
- [ADK — LiteLLM model integration](https://adk.dev/agents/models/litellm/)
- [google/adk-python #4981 — litellm quarantine breaks `eval` / `extensions` extras](https://github.com/google/adk-python/issues/4981)
- [google/adk-python #5024 — DeepSeek multi-tool-call parse failure](https://github.com/google/adk-python/issues/5024)
- [google-adk on PyPI — 2.6.3, 2026-08-07](https://pypi.org/project/google-adk/)
- [DeepSeek API Docs — Thinking Mode (`extra_body`, `reasoning_content` passback)](https://api-docs.deepseek.com/guides/thinking_mode/)
- [DeepSeek API Docs — Tool Calls](https://api-docs.deepseek.com/guides/tool_calls/)
- [anomalyco/opencode #24130 — `reasoning_content` must be passed back with tools](https://github.com/anomalyco/opencode/issues/24130)
- [Graphify-Labs/graphify #1621 — thinking enabled by default causes JSON parse failure](https://github.com/Graphify-Labs/graphify/issues/1621)
- [litellm on PyPI — 1.95.0, 2026-08-02](https://pypi.org/project/litellm/)
- [LiteLLM — Security update, March 2026 incident guidance](https://docs.litellm.ai/blog/security-update-march-2026)
- [BerriAI/litellm #20982 — `extra_body` not passed through](https://github.com/BerriAI/litellm/issues/20982)
- [OSMF — Tile Usage Policy (offline and bulk download prohibited)](https://operations.osmfoundation.org/policies/tiles/)
- [OpenMapTiles — self-hosted vector tiles](https://openmaptiles.org/)
- [DeepSeek V4 pricing and peak-hour surcharge](https://www.explainx.ai/blog/deepseek-v4-official-release-peak-pricing-mid-july-2026)
