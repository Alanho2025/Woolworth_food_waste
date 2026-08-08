# FoodFlow Auckland Clean Code Specification

- **Document Purpose:** Convert “maintainable, extensible, and free from critical code smells” into an executable engineering contract for the FoodFlow Auckland hackathon MVP.
- **Scope:** Python FastAPI backend, Google ADK autonomous Agent, DeepSeek integration, React/Next.js frontend, SQLite persistence, tests, scripts, and shared contracts.
- **Primary Users:** Human and AI coding contributors.
- **Product Focus:** One pitch-ready core journey:
  **Donate → Agent Match → Driver Route → Partial Acceptance → Automatic Rematch → Completed Delivery**
- **Non-goal:** This document does not require production-scale architecture, enterprise security, microservices, or abstractions for future features that are outside the MVP.

## 1. Specification Language

- **MUST:** Violation blocks completion of the MVP.
- **SHOULD:** Follow by default; exceptions require a documented reason.
- **MAY:** Optional when it improves the core journey without delaying it.
- **Review threshold:** A signal to simplify or split code, not an automatic failure.

## 2. Core Engineering Principles

### 2.1 Single Responsibility

Every module, class, function, React component, Google ADK tool, and Agent step MUST have one primary responsibility describable in one sentence.

Examples:

- `create_donation_request` creates and validates a donation request.
- `validate_recipient_capacity` checks whether a community can receive a quantity.
- `create_delivery_order` persists one valid delivery order.
- `RematchPanel` displays the rematch result.

A unit that repeatedly requires “and” in its responsibility should be split.

### 2.2 Explicit Dependency Direction

Dependencies MUST flow in one direction:

```text
Frontend / FastAPI route
          ↓
Application use case
          ↓
Domain policy and typed contracts
          ↓
Port / Protocol
          ↓
Infrastructure adapter
SQLite / DeepSeek / Google ADK / route simulation
```

Rules:

- API routes MUST delegate business decisions to application services.
- Domain code MUST NOT import FastAPI, SQLAlchemy, Google ADK, DeepSeek SDKs, React, or browser APIs.
- Infrastructure adapters MAY implement inner-layer protocols.
- React components MUST NOT contain backend allocation rules.
- The Agent MUST NOT write directly to database tables.

### 2.3 Agent Decision vs Product State

Use this responsibility split:

- **DeepSeek decides:** creates a concise plan, compares feasible recipients, chooses recipient and quantity, and decides whether rematching is required.
- **Google ADK orchestrates:** manages the bounded plan-and-action loop and tool calls.
- **Python tools validate and execute:** retrieve facts, enforce hard constraints, reserve inventory, create orders, update delivery status, and persist audit records.
- **FastAPI exposes workflows.**
- **React presents the pitch journey.**
- **SQLite stores operational truth.**

The Agent MUST submit structured action proposals through typed tools.

The Agent MUST NOT:

- execute raw SQL;
- mutate ORM models directly;
- bypass validation;
- invent quantity, capacity, route time, recipient status, or delivery completion;
- write hidden chain-of-thought to logs or the UI.

## 3. MVP Code Organization

```text
backend/
  app/
    api/                 # FastAPI routes only
    application/         # use cases and transaction coordination
    domain/              # pure entities, policies, and state transitions
    contracts/           # Pydantic request/result/tool schemas
    agents/              # Google ADK Agent, instructions, model factory
    agents/tools/        # focused read, validation, and action tools
    infrastructure/      # SQLite repositories, DeepSeek adapter, route simulator
    seed/                # deterministic pitch data
  tests/
    unit/
    integration/
    agent_eval/

frontend/
  src/
    app/                 # routing and global providers
    pages/               # page composition
    features/
      dashboard/
      donate/
      agent-match/
      driver-route/
      delivery-confirmation/
      rematch/
    shared/              # stable UI primitives and API client
  tests/
```

`shared` MUST NOT become a dumping ground.

Create a shared abstraction only when:

- two existing use cases genuinely share behavior;
- an external provider needs a replaceable adapter;
- testing requires isolating I/O;
- or the Agent contract requires multiple implementations.

Do not create generic managers, base repositories, universal factories, or unnecessary provider layers “for the future.”

## 4. Core Domain Contracts

Use typed models for at least:

- `DonationRequest`
- `FoodItem`
- `CommunityOrganisation`
- `CommunityRequest`
- `Driver`
- `DeliveryOrder`
- `AllocationDecision`
- `RematchDecision`
- `AgentRun`
- `AuditEvent`

Important distinctions:

- **Need:** what a community currently wants.
- **Capacity:** what it can currently receive and store.
- **Eligibility:** whether hard constraints allow a delivery.
- **Agent decision:** which eligible option is selected and why.

SQLAlchemy models represent persistence only.

Pydantic models represent API, Agent, and tool contracts.

Do not use SQLAlchemy models directly as API responses.

## 5. General Clean Code Rules

### 5.1 Naming

Names MUST describe FoodFlow domain intent.

Use:

- `remaining_inventory_kg`
- `recipient_has_chilled_capacity`
- `validate_receiving_window`
- `create_delivery_order`
- `record_partial_acceptance`

Avoid:

- `handle_data`
- `process_item`
- `manager`
- `helper`
- `utils2`

Use one term consistently. Do not mix `charity`, `receiver`, and `community` for the same entity unless the distinction is intentional and documented.

### 5.2 Functions

- Functions SHOULD do one thing.
- Commands and queries SHOULD be separate.
- Read functions MUST NOT produce hidden writes.
- Public inputs and outputs MUST be explicitly typed.
- Core domain data MUST NOT be passed as untyped dictionaries.
- More than 5 parameters is a review threshold.
- More than 3 nesting levels is a review threshold.
- More than 50 executable lines is a review threshold.
- Cyclomatic complexity above 10 is a review threshold.
- Boolean flags MUST NOT make one function perform unrelated flows.

### 5.3 Modules and Components

- Python modules over 500 handwritten executable lines require review.
- React components over 250 lines require review.
- A React component that fetches data, transforms business rules, manages forms, and renders the whole page MUST be split.
- Classes named `Service`, `Manager`, `Helper`, or `Utils` that absorb unrelated responsibilities are considered a God Object smell.

### 5.4 Comments and Documentation

Comments SHOULD explain:

- why a constraint exists;
- an external integration limitation;
- an Agent/tool safety boundary;
- a non-obvious trade-off.

Do not keep:

- commented-out code;
- stale comments;
- comments that only repeat the code.

`TODO`, `FIXME`, lint suppressions, and type ignores MUST include a reason and issue reference.

## 6. Backend Rules

### 6.1 Type Safety

- All application, domain, Agent, and tool public functions MUST have complete type annotations.
- Pydantic v2 MUST validate API requests, Agent outputs, and tool inputs/outputs.
- `Any`, `cast`, and `# type: ignore` MUST be limited to the smallest adapter boundary and explained.

### 6.2 Transactions

The application layer defines transaction boundaries.

A successful allocation transaction SHOULD include:

1. validate current inventory;
2. validate recipient capacity;
3. reserve inventory;
4. reserve recipient capacity;
5. create delivery order;
6. create audit event.

If any step fails, the transaction MUST roll back.

The success audit belongs to that same transaction and MUST roll back with it.
A failure audit is different operational evidence: after the failed product
transaction has rolled back, it MUST be written and committed through a separate
connection so the rejected attempt remains diagnosable. Failure-audit persistence
MUST NOT make any partial inventory, capacity, or delivery-order write durable.

The success audit event belongs to that same transaction. A failed allocation attempt MUST be
audited only after the failed transaction has rolled back, using an independent transaction, so
the audit evidence survives without allowing any partial inventory, capacity, or delivery write
to survive. Failure-audit persistence MUST NOT turn a failed business operation into success or
include secrets, provider payloads, or hidden reasoning.

Partial acceptance MUST:

1. preserve the accepted quantity;
2. return only the rejected quantity to active inventory;
3. avoid duplicate quantity;
4. trigger rematching for only the remaining quantity.

### 6.3 Error Handling

Expected failures MUST use typed errors, for example:

- `RECIPIENT_CATEGORY_UNSUPPORTED`
- `RECIPIENT_CAPACITY_EXCEEDED`
- `STORAGE_INCOMPATIBLE`
- `RECEIVING_WINDOW_CLOSED`
- `DRIVER_CAPACITY_EXCEEDED`
- `DUPLICATE_ALLOCATION`
- `AGENT_OUTPUT_INVALID`
- `AGENT_STEP_LIMIT_REACHED`

Do not parse exception message strings to determine business outcomes.

Do not catch broad exceptions and return success.

Retries are allowed only for transient provider failures and MUST include:

- maximum attempts;
- timeout;
- backoff;
- idempotency protection.

### 6.4 Configuration

Secrets MUST come from environment variables.

At minimum:

```text
DEEPSEEK_API_KEY
DEEPSEEK_BASE_URL
DEEPSEEK_MODEL
DATABASE_URL
DEMO_MODE
```

Environment variables are read only in the configuration boundary.

Do not expose DeepSeek credentials to the frontend.

## 7. Google ADK and DeepSeek Rules

### 7.1 Agent Structure

Use one root Agent:

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

The loop MUST have:

- a maximum step count;
- a timeout;
- bounded tool use;
- explicit stop conditions;
- structured failure statuses.

### 7.2 Agent State

Agent state MUST be:

- typed;
- minimal;
- serializable;
- based on IDs and structured facts.

Do not store:

- raw hidden reasoning;
- unbounded transcripts;
- full database objects;
- secrets.

### 7.3 Prompts and Model Boundaries

Prompts, tool schemas, and output schemas MUST be centrally managed under `backend/app/agents/`.

Do not scatter Agent instructions across:

- API routes;
- React components;
- repository queries;
- database records.

Model output is untrusted until it passes:

1. schema validation;
2. hard-constraint validation;
3. current-state validation;
4. transaction validation.

The UI may show:

- concise Agent plan;
- facts used;
- excluded recipients;
- exclusion reasons;
- chosen recipient;
- action result;
- rematch result.

The UI MUST NOT show hidden chain-of-thought.

### 7.4 Tool Rules

Each tool MUST have:

- typed input and output;
- one focused responsibility;
- clear docstring;
- timeout when I/O is involved;
- typed failure codes;
- sanitized traces.

Read tools MUST NOT write.

Action tools MUST be idempotent where practical.

Required MVP tools may include:

```text
get_donation
list_candidate_communities
get_community_capacity
get_available_drivers
calculate_route
validate_category_acceptance
validate_storage_compatibility
validate_recipient_capacity
validate_receiving_window
validate_driver_capacity
reserve_inventory
reserve_recipient_capacity
create_delivery_order
assign_driver
record_partial_acceptance
release_remaining_inventory
create_rematched_delivery
update_driver_route
```

Do not add tools that are not needed by the pitch journey.

## 8. Frontend Rules

### 8.1 Pitch-First Screens

The frontend MUST clearly present this sequence:

1. **Dashboard**
2. **Donate**
3. **Agent Match**
4. **Driver Route**
5. **Delivery Confirmation**
6. **Automatic Rematch**
7. **Final Success State**

The UI is part of the MVP value, not a secondary layer.

### 8.2 Agent Match Screen

The screen SHOULD visually show:

- donation summary;
- candidate community cards;
- need;
- capacity;
- storage compatibility;
- receiving window;
- excluded alternatives;
- concise Agent plan;
- selected recipient;
- created delivery order.

Do not reduce the screen to a chatbot transcript.

### 8.3 Driver Route Screen

The screen SHOULD show:

- pickup location;
- recipient location;
- food and quantity;
- simple Auckland map;
- simulated route;
- delivery status;
- delivery deadline;
- concise driver instructions.

Real GPS and commercial routing are not required.

### 8.4 Automatic Rematch Screen

This is the key pitch screen.

It MUST show:

- planned quantity;
- accepted quantity;
- remaining quantity;
- remaining inventory returning to the network;
- new candidate comparison;
- new selected recipient;
- old route versus updated route;
- final rescued quantity;
- no duplicate quantity.

### 8.5 Type and State Safety

- TypeScript strict mode MUST be enabled.
- API responses MUST be generated from or validated against backend contracts.
- Do not manually duplicate inconsistent interfaces.
- Server state MUST be managed through one query layer.
- Formal state MUST remain authoritative in the backend.
- The frontend MUST explicitly show loading, blocked, retryable error, and completed states.
- Tests SHOULD verify visible behavior rather than component internals.

## 9. Code Smells That Block Completion

The following block completion:

| Code Smell | Required Fix |
| --- | --- |
| Circular dependency | Correct ownership or introduce a clear port |
| Agent writes directly to database | Route through typed action tool and application service |
| SQLAlchemy model used as public API schema | Add independent Pydantic contract |
| Untyped core dictionary | Replace with typed model |
| Swallowed exception | Return typed failure |
| Mutable global state | Use dependency injection or scoped state |
| Hidden network or database I/O | Move to explicit adapter |
| Duplicate allocation logic | Centralize in one domain policy |
| Frontend duplicates backend eligibility rules | Backend remains authoritative |
| Unbounded Agent loop | Add step, timeout, and tool budgets |
| Hardcoded secrets | Move to environment configuration |
| Dead or commented-out code | Delete it |
| Primary UI button does nothing | Implement the action or remove the button |

Mandatory review signals:

- a small change touches many unrelated modules;
- the same constraint is reimplemented in backend, frontend, and prompt;
- N+1 database or API calls;
- hidden call-order dependency;
- a page component centralizes fetching, business logic, and rendering;
- a tool combines retrieval, validation, persistence, and UI formatting.

## 10. Testing Contract

### 10.1 Required Tests

Backend unit tests:

- category acceptance;
- storage compatibility;
- recipient capacity;
- receiving window;
- driver capacity;
- remaining inventory;
- duplicate allocation prevention;
- partial acceptance quantity calculation.

Integration tests:

- donation submission to Agent run;
- valid match to delivery order;
- invalid recipient exclusion;
- partial acceptance to rematch;
- rematch creates a new delivery without duplicating quantity.

Agent evaluation:

- Agent selects a feasible recipient;
- Agent does not select an invalid recipient;
- Agent uses correct tools;
- Agent re-plans after a typed tool failure;
- Agent rematches only the remaining quantity;
- Agent explanation is grounded in tool results.

Frontend tests:

- Donate form generates JSON preview;
- Agent Match displays excluded and selected communities;
- Driver Route displays the correct delivery;
- Delivery Confirmation records partial acceptance;
- Rematch screen displays the new recipient and remaining quantity.

One end-to-end test MUST cover:

```text
Donate
→ Agent Match
→ Delivery Order
→ Partial Acceptance
→ Automatic Rematch
→ Completed Delivery
```

### 10.2 Test Quality

- Test names MUST describe state, action, and expected outcome.
- Bug fixes MUST include regression tests.
- Mocks MAY isolate DeepSeek, time, routing, or other uncontrollable I/O.
- Mocks MUST NOT replace the core allocation and quantity policy being tested.
- Do not hide flaky tests by repeatedly rerunning them.

## 11. MVP Quality Gate

All completed changes MUST pass:

```yaml
quality_gate:
  backend:
    format: required
    lint: required
    typecheck: required
    tests: required
  frontend:
    format: required
    lint: required
    typecheck: required
    tests: required
  agent:
    schema_validation: required
    bounded_loop_check: required
    core_eval: required
  architecture:
    forbidden_import_check: required
    dependency_cycle_check: required
  security:
    secret_scan: required
  journey:
    end_to_end_core_flow: required
```

Recommended tools:

- Ruff
- mypy
- pytest
- TypeScript compiler
- ESLint
- Vitest
- Playwright

Local and CI commands MUST call the same scripts.

## 12. Definition of Done

The FoodFlow MVP is complete only when:

- the core pitch journey works end to end;
- the UI clearly shows the Agent’s value;
- Google ADK is used for the Agent loop;
- DeepSeek is used for planning and final recipient selection;
- Python tools enforce hard constraints;
- no routine human approval is required;
- partial acceptance returns only the remaining quantity;
- automatic rematching works;
- no quantity is duplicated;
- frontend and backend type checks pass;
- required tests pass;
- primary UI controls work;
- no secrets are exposed;
- no blocker code smells remain;
- implemented, simulated, and unverified features are clearly distinguished.

## 13. Out of Scope

Do not expand this specification to require:

- image processing;
- barcode scanning;
- live GPS;
- production authentication;
- advanced RBAC;
- PostgreSQL migration;
- microservices;
- event buses;
- real notification infrastructure;
- full fleet optimisation;
- predictive forecasting;
- IoT monitoring;
- production compliance automation;
- native mobile applications;
- broad analytics beyond the pitch journey.

The code should be clean enough to extend later, but the MVP MUST prioritise a polished and reliable core journey over architecture for hypothetical future features.
