# AGENTS.md — FoodFlow Auckland Coding Agent Instructions

This root-level file applies to all human and AI coding contributors modifying FoodFlow Auckland code, tests, schemas, configuration, prompts, or runtime documentation.

## 1. Product Mission

FoodFlow Auckland is a hackathon MVP for autonomous surplus-food redistribution.

Its purpose is to demonstrate one clear, pitch-ready journey:

**Woolworths Donate → AI Match → Driver Route → Partial Acceptance → Automatic Rematch → Completed Delivery**

The product must show that the system can:

- receive a structured Woolworths donation request;
- compare community need, capacity, storage, receiving windows, and route feasibility;
- let a DeepSeek-powered Google ADK Agent select a feasible recipient;
- automatically create a delivery order and assign a driver;
- display the decision and route clearly in the UI;
- recover when the first recipient only partially accepts or rejects the delivery;
- rematch only the remaining quantity without duplication.

This is not:

- a consumer grocery application;
- a generic chatbot;
- a food-waste reporting dashboard;
- a production fleet-management platform;
- a predictive forecasting product;
- or a production compliance system.

The UI is a primary part of the MVP. A technically correct backend with a weak or unclear pitch journey is not considered complete.

## 2. Current Project Status

Treat documentation as target behavior unless source code, tests, and reproducible execution prove implementation.

Contributors MUST:

- distinguish implemented, simulated, configured, and planned functionality;
- not claim Google ADK, DeepSeek, matching, routing, or rematching works solely because documentation exists;
- use source code, tests, traces, and actual execution as evidence;
- update relevant documentation when implementation status changes.

The demo may use deterministic seeded community, driver, and route data, but simulated functionality must be visibly labelled.

## 3. Required Reading Before Code Changes

Before planning or modifying runtime code, read:

1. `README.md`
2. `docs/clean_code_spec.md`
3. the current FoodFlow MVP generation prompt or product specification
4. relevant API, Agent, or UI contracts for the requested change

Read additionally by change type:

| Change Type | Additional Required Reading |
| --- | --- |
| Donate flow or JSON contract | Donation request schemas and Donate page specification |
| Community matching | Need, capacity, eligibility, and hard-constraint rules |
| Google ADK Agent, prompt, tool, or eval | Agent instructions, tool contracts, output schema, and eval cases |
| Delivery, driver, or rematch | Delivery state and quantity-allocation rules |
| Frontend or pitch journey | UI screen requirements and core demo flow |
| Database or persistence | SQLAlchemy models, transaction rules, and test fixtures |
| README or product claims | Current implementation evidence and known limitations |

Do not rely only on an earlier summary when a new code-changing task begins.

## 4. Source of Truth and Conflict Handling

| Topic | Authoritative Source |
| --- | --- |
| Product mission and MVP scope | README and current FoodFlow MVP prompt/specification |
| Clean code, testing, and Definition of Done | `docs/clean_code_spec.md` |
| API, tool, and Agent contracts | Pydantic schemas and Agent/tool specification |
| Matching hard constraints | Domain policies and validation tests |
| Implemented runtime behavior | Source code, tests, database schema, and reproducible execution |
| UI behavior | Current frontend code plus approved pitch journey specification |

If sources conflict:

1. identify the conflicting files and impact;
2. do not silently implement the most convenient version;
3. harmonize only when the change is clearly an implementation detail;
4. ask the user when the conflict changes product scope, matching responsibility, data ownership, or UI behavior;
5. update affected source-of-truth documents within the same change.

## 5. Approved Technology Direction

Unless the user explicitly approves an architecture change, use:

- **Frontend:** Next.js App Router, React, TypeScript strict mode
- **Styling:** Tailwind CSS, shadcn/ui or accessible custom components
- **Server state:** TanStack Query
- **Forms:** React Hook Form + Zod
- **Backend:** Python 3.12+, FastAPI, Pydantic v2
- **Persistence:** SQLAlchemy 2 + SQLite for the MVP
- **Agent framework:** Google ADK Python SDK
- **Model provider:** DeepSeek API through a supported OpenAI-compatible integration
- **Map:** Leaflet or MapLibre with deterministic Auckland demo routes
- **Tests:** pytest, Vitest, Playwright, bounded Agent evals
- **Quality:** Ruff, mypy, TypeScript compiler, ESLint

Do not introduce on your own:

- LangGraph;
- CrewAI;
- LangChain;
- microservices;
- Kubernetes;
- Redis;
- Celery;
- PostgreSQL migration work;
- a standalone vector database;
- multi-Agent orchestration;
- real GPS or fleet-optimisation infrastructure;
- image processing;
- barcode scanning.

Before adding a significant dependency, explain:

- which current requirement cannot be met;
- why the existing stack is insufficient;
- maintenance and removal cost;
- how the dependency will be isolated and tested.

All versions must be pinned in manifest or lock files.

## 6. Architecture Boundaries

Dependency direction:

```text
Frontend / FastAPI route
          ↓
Application use case
          ↓
Domain policy and typed contract
          ↓
Port / Protocol
          ↓
Infrastructure adapter
SQLite / DeepSeek / Google ADK / route simulation
```

MUST rules:

- API routes handle transport, parsing, dependency injection, and response mapping only.
- Application services coordinate use cases and transactions.
- Domain code does not import FastAPI, SQLAlchemy, Google ADK, DeepSeek SDKs, React, or browser APIs.
- Infrastructure adapters do not make final product-policy decisions.
- React components do not implement authoritative allocation or quantity rules.
- Circular dependencies are prohibited.
- Generic `manager`, `helper`, or `utils` dumping grounds are prohibited.
- Build the smallest complete vertical slice first.
- Create abstractions only after real duplication or a clear provider boundary exists.

## 7. Agent and Product-State Boundary

Use this responsibility split:

- **DeepSeek decides:** plans, compares feasible recipients, chooses recipient and quantity, decides whether to split or rematch, and explains the decision.
- **Google ADK orchestrates:** controls the bounded plan-and-action loop and invokes tools.
- **Python tools validate and execute:** retrieve facts, enforce constraints, reserve quantities, create orders, update delivery state, and persist audit records.
- **SQLite stores operational truth.**
- **React presents the user-visible journey.**

The Agent MUST NOT:

- write directly to SQLAlchemy models;
- execute raw SQL;
- bypass validation;
- invent quantities, capacity, route duration, recipient availability, or delivery completion;
- persist hidden chain-of-thought;
- expose secrets or provider internals.

All model outputs are untrusted until they pass:

1. Pydantic schema validation;
2. hard-constraint validation;
3. current-state validation;
4. transaction validation.

Do not create a generic `save_agent_output` function that writes model output directly to product tables.

## 8. Core Product Rules

### 8.1 Donation

A donation request must contain:

- store;
- pickup window;
- at least one food item;
- item name;
- category;
- positive quantity;
- unit;
- storage requirement;
- relevant expiry or operational deadline where needed.

Do not invent missing values.

### 8.2 Need, Capacity, and Eligibility

Keep these concepts separate:

- **Need:** what a community currently wants.
- **Capacity:** what it can currently receive and store.
- **Eligibility:** whether hard constraints allow a delivery.
- **Agent decision:** which eligible option is selected.

A community may need meat but still be ineligible because chilled capacity is zero.

### 8.3 Hard Constraints

Backend validation MUST reject allocations that:

- exceed available inventory;
- allocate the same quantity twice;
- exceed remaining recipient capacity;
- use an unsupported category;
- violate chilled or frozen storage requirements;
- arrive outside receiving hours;
- miss the operational deadline;
- use an unavailable or incompatible driver;
- exceed vehicle capacity;
- create an invalid delivery-state transition.

### 8.4 Partial Acceptance and Rematch

When a recipient partially accepts a delivery:

1. preserve the accepted quantity;
2. calculate the remaining quantity;
3. return only the remaining quantity to active inventory;
4. do not duplicate or recreate the accepted quantity;
5. trigger rematching only for the remainder;
6. create a new valid destination and route when feasible;
7. show the update clearly in the UI.

This quantity integrity rule is a blocker-level requirement.

## 9. Google ADK Agent Rules

FoodFlow uses one root Agent:

```text
FoodRedistributionAgent
```

Its bounded loop is:

```text
Observe
→ Plan
→ Retrieve facts
→ Compare feasible options
→ Validate
→ Execute
→ Re-plan if needed
→ Finish
```

MUST rules:

- Agent state is typed, minimal, serializable, and ID/reference based.
- The loop has step, tool, timeout, and token budgets.
- Stop conditions and failure states are explicit.
- Tool selection uses typed schemas.
- Write tools are idempotent where practical.
- Read tools do not produce hidden write side effects.
- Tool failures are distinguishable as validation failure, not found, timeout, rate limited, invalid result, or internal failure.
- Raw hidden reasoning is never stored or displayed.
- The UI displays only concise plans, facts, exclusions, decisions, actions, and rematch outcomes.
- Prompts, tool schemas, model configuration, and output schemas are centrally managed under the Agent layer.

Do not add tools that are not required for the pitch journey.

## 10. DeepSeek Integration Rules

- `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, and `DEEPSEEK_MODEL` come from environment configuration.
- Keys must never enter the frontend bundle, logs, snapshots, prompts, or test fixtures.
- Use the installed Google ADK version's supported OpenAI-compatible integration.
- Keep provider-specific code isolated in one adapter or model-factory module.
- Live model calls require explicit timeout, bounded retries, and clear failure reporting.
- Deterministic tests and demo fixtures must exist so the core journey remains testable without a live key.
- Do not claim live verification when only fixture or mock tests were run.

## 11. Frontend and Pitch Rules

The frontend MUST support and visually emphasize:

1. Dashboard
2. Donate
3. Agent Match
4. Driver Route
5. Delivery Confirmation
6. Automatic Rematch
7. Final Success State

### 11.1 Dashboard

Show only pitch-relevant status, such as:

- active donation;
- food at risk;
- selected recipient;
- current delivery;
- remaining quantity after partial acceptance.

Do not build broad analytics that do not support the journey.

### 11.2 Agent Match

The UI SHOULD show:

- donation summary;
- candidate community cards;
- need;
- remaining capacity;
- storage compatibility;
- receiving window;
- excluded alternatives;
- exclusion reasons;
- concise Agent plan;
- selected recipient;
- delivery order created.

Do not make the primary experience a chatbot transcript.

### 11.3 Driver Route

Show:

- pickup and destination;
- food and quantity;
- simple Auckland map;
- simulated route;
- delivery status;
- deadline;
- concise driver instructions.

Real GPS and commercial route optimisation are not required.

### 11.4 Automatic Rematch

This is the key pitch screen.

It MUST visibly show:

- planned quantity;
- accepted quantity;
- remaining quantity;
- remaining inventory returning to the network;
- new candidate comparison;
- new selected recipient;
- updated route;
- final rescued quantity;
- proof that quantity was not duplicated.

### 11.5 Frontend State

- TypeScript strict mode is mandatory.
- Server state uses one query layer.
- Formal allocation and delivery state remain authoritative in the backend.
- UI must explicitly show loading, blocked, retryable error, and completed states.
- Tests verify visible behavior rather than component internals.
- A primary button that does nothing blocks completion.

## 12. Clean Code Hard Gates

All code MUST comply with `docs/clean_code_spec.md`.

Specifically prohibited:

- circular dependencies;
- Agent direct database writes;
- SQLAlchemy models used as public schemas;
- untyped core dictionaries;
- mutable global runtime state;
- hidden network or database I/O;
- swallowed broad exceptions;
- duplicate quantity or capacity rules;
- frontend copies of backend hard constraints;
- dead code;
- commented-out code;
- debug `print`;
- unjustified lint disables, type ignores, `Any`, `as any`, or test skips;
- unbounded Agent or tool loops;
- hardcoded credentials;
- hidden reasoning in logs or UI.

Blocker or critical smells do not accept exceptions.

## 13. Required Working Method

### Before editing

1. Read required source-of-truth documents.
2. Inspect repository status and existing uncommitted changes.
3. Do not overwrite or revert user changes.
4. Search for existing contracts, implementations, and tests.
5. Explain current behavior, target behavior, affected boundaries, and verification method.
6. Create a short plan for multi-file, schema, Agent, or cross-layer changes.
7. Ask the user only when uncertainty could change product direction, matching responsibility, data ownership, or public contracts.

### While editing

1. Implement the smallest complete vertical slice.
2. Preserve typed contracts and dependency direction.
3. Add tests with behavior changes.
4. Bug fixes require regression tests.
5. Do not lower assertions or disable gates to make tests pass.
6. Do not expand into unrelated production infrastructure.
7. If runtime behavior differs from the specification, resolve or document the discrepancy.

### After editing

1. Run the smallest targeted verification first.
2. Then run applicable format, lint, typecheck, unit, integration, Agent eval, and E2E gates.
3. Inspect the diff for secrets, debug code, dead files, suppressions, and documentation drift.
4. Report the exact commands run and actual results.
5. Clearly state what was not verified, including live DeepSeek or browser checks.
6. Stop development processes started by the task.
7. Do not terminate processes that existed before the task.

## 14. Issue Logging and Three-Attempt Limit

For issues affecting correctness, quantity integrity, Agent behavior, state transitions, test gates, or pitch completion:

- create or update `docs/issues/pending-issues.md`;
- record root cause, hypothesis, change, result, and evidence;
- allow a maximum of three substantive remediation attempts for the same root cause;
- do not count read-only inspection as an attempt;
- do not rerun the same command without a new hypothesis;
- after the third failed attempt, stop modifying that issue and report the blocker;
- do not lower quality gates or silently mark the issue resolved.

Pure typos and one-step mechanical formatting fixes do not require issue logging.

## 15. Context and Scope Discipline

The development goal is a polished core journey, not broad platform coverage.

Use this search and verification order:

```text
precise search
→ relevant contract
→ targeted file range
→ targeted test
→ broader repository reading only when needed
```

Do not:

- repeatedly reread the whole repository;
- repeatedly paste large logs;
- rerun full gates without a source change or reason;
- add unrelated features because they appear useful;
- introduce architecture for hypothetical future requirements.

Live DeepSeek validation comes after deterministic schema, tool, policy, and failure tests.

## 16. Verification Matrix

| Change | Minimum verification |
| --- | --- |
| Python domain policy | Ruff, mypy, targeted pytest |
| FastAPI application flow | Above + API/integration/error-path tests |
| SQLAlchemy model/query | Above + transaction and persistence integration test |
| Google ADK prompt/tool | Schema test, policy test, failure test, bounded Agent eval |
| DeepSeek adapter | Deterministic adapter tests + optional live smoke test |
| React component/hook | ESLint, TypeScript strict, Vitest |
| Core pitch journey | Above + Playwright E2E |
| Documentation only | Formatting/link consistency and no false runtime claims |

Do not fabricate passing commands or tests that do not exist.

## 17. Required Test and Eval Coverage

At minimum, verify:

- valid donation submission;
- invalid donation rejection;
- community category exclusion;
- storage incompatibility;
- capacity limit;
- receiving-window exclusion;
- valid recipient selection;
- automatic delivery-order creation;
- driver assignment;
- partial acceptance quantity calculation;
- remaining inventory restoration;
- automatic rematch;
- no duplicate allocation;
- Agent recovery after typed tool failure;
- Agent explanation grounded in tool results;
- full UI journey.

One end-to-end test MUST cover:

```text
Donate
→ Agent Match
→ Driver Route
→ Partial Acceptance
→ Automatic Rematch
→ Completed Delivery
```

Mocks may isolate DeepSeek, time, and route I/O.

Mocks must not replace the core quantity, capacity, or eligibility policies being tested.

## 18. External Action and Tool Policy

- Prioritize read-only inspection first.
- File edits are limited to the requested repository and task scope.
- Do not use destructive git commands.
- Do not revert unrelated user changes.
- Do not commit, push, deploy, send messages, or modify external systems unless explicitly requested.
- Technical web research should prioritize official and primary sources.
- Credentials are injected only into the adapter that needs them.
- Long-running Agent operations must be bounded and cancellable.
- The runtime must not depend on a developer-local connector or MCP setup.

## 19. Documentation Rules

- Documentation is primarily in English.
- Code identifiers, schemas, APIs, and technical terms remain in English.
- Explain behavior by workflow, not only by file tree.
- Clearly distinguish:
  - implemented;
  - simulated;
  - configured but unverified;
  - planned.
- Update public contracts and significant Agent behavior in the same change.
- Do not claim production or live-provider validation when only local fixtures were used.

## 20. Completion Report

For a code-changing task, the final report must state:

- outcome;
- files changed;
- user-visible behavior added or changed;
- architecture and Agent boundaries maintained;
- commands actually run;
- test and build results;
- live or browser gates not run;
- assumptions;
- blockers or remaining risks.

Do not reply only with “done”, “tests passed”, or “should be fine”.

## 21. Definition of Done

A task is complete only when:

- requested behavior is implemented without unauthorized scope expansion;
- the core pitch journey remains intact;
- UI clearly shows Agent value;
- Google ADK remains the Agent framework;
- DeepSeek remains the planning and decision model;
- Python tools remain the validation and execution boundary;
- no routine human approval is introduced;
- partial acceptance rematches only the remaining quantity;
- no inventory quantity is duplicated;
- applicable format, lint, type, test, Agent eval, and E2E gates pass or are explicitly reported as unverified;
- there are no blocker code smells, secrets, debug artifacts, or untracked suppressions;
- documentation matches runtime evidence;
- existing user changes are preserved.

If these conditions cannot be met, report the specific blocker and safe next step rather than lowering the standard.
