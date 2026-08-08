You are a senior full-stack engineer, Python backend engineer, Google ADK Agent architect, product designer, and QA engineer.

Build a polished hackathon MVP named “FoodFlow Auckland”.

The product connects Woolworths stores, Auckland community organisations, and delivery drivers.

The MVP must demonstrate one complete visible journey:

Woolworths creates a donation
→ the AI Agent compares community demand and capacity
→ the best feasible organisation is selected
→ a delivery order and driver route are created
→ the driver begins delivery
→ the recipient can only accept part of the food
→ the remaining food is automatically rematched
→ the route updates
→ all food is delivered.

The pitch must make the system’s intelligence visible through the UI.

Do not hide the core value in backend logs.
Do not reduce the demo to plain forms and tables.
Do not build a large number of disconnected features.
Do not remove visible features that help judges understand the Agent, matching logic, route, and recovery flow.

The complete demo must be understandable in approximately 2–3 minutes.

==================================================
1. CORE DEMO STORY
==================================================

Use one fixed demo scenario.

Woolworths Mount Eden submits a donation containing:

- 60 kg of fresh vegetables
- ambient storage
- pickup window: 4:00 pm–5:00 pm
- delivery deadline: 7:00 pm

Seed four community organisations:

Community A:
- urgently needs vegetables
- can accept 60 kg
- is open
- initially appears to be the best destination

Community B:
- does not accept fresh vegetables

Community C:
- accepts vegetables
- has only 10 kg remaining capacity

Community D:
- accepts vegetables
- has 30 kg remaining capacity
- is open
- is feasible as a secondary destination

The Agent initially allocates 60 kg to Community A.

During delivery, Community A reports that it can now accept only 35 kg.

The Agent must then:

1. keep 35 kg assigned to Community A;
2. return the remaining 25 kg to active inventory;
3. automatically compare other organisations;
4. exclude Community B because the category is unsupported;
5. exclude Community C because capacity is insufficient;
6. select Community D;
7. update the driver route;
8. show the rematch explanation;
9. complete delivery of all 60 kg without duplication.

This is the single journey the whole MVP must support.

==================================================
2. REQUIRED USER-FACING SCREENS
==================================================

Build six visually strong screens.

1. Operations Dashboard
2. Woolworths Donate
3. AI Match Decision
4. Driver Route
5. Delivery Confirmation
6. Automatic Rematch

These screens must feel like one connected product, not separate mock-ups.

==================================================
3. SCREEN 1 — OPERATIONS DASHBOARD
==================================================

The dashboard is the opening pitch screen.

It should immediately communicate:

- active surplus available;
- food already matched;
- food currently in transit;
- food at risk;
- active deliveries;
- community demand;
- live Auckland network status.

Required visual elements:

- large KPI cards;
- Auckland map with Woolworths, communities, and drivers;
- one highlighted urgent donation card;
- one active Agent decision card;
- one active delivery card;
- one alert showing a community capacity change;
- one small impact summary such as kilograms rescued.

Keep text short.

The dashboard must visually show that this is an active coordination system, not only a reporting page.

Primary CTA:

“Create Donation”

==================================================
4. SCREEN 2 — WOOLWORTHS DONATE
==================================================

Do not implement image processing.

Create a structured donation form that generates a JSON request.

Required fields:

- store;
- food name;
- category;
- quantity;
- unit;
- storage requirement;
- pickup window;
- delivery deadline;
- handling notes.

Show a live JSON preview beside the form.

Example:

{
  "donation_id": "DON-001",
  "store_id": "WW-MT-EDEN",
  "pickup_window": {
    "start": "2026-08-08T16:00:00+12:00",
    "end": "2026-08-08T17:00:00+12:00"
  },
  "items": [
    {
      "item_name": "Fresh vegetables",
      "category": "vegetables",
      "quantity": 60,
      "unit": "kg",
      "storage_type": "ambient",
      "delivery_deadline": "2026-08-08T19:00:00+12:00"
    }
  ]
}

Required UI features:

- clear step indicator;
- prefilled demo-data button;
- live validation;
- JSON preview;
- prominent “Submit to AI Agent” button.

After submission, transition directly into the AI Match Decision screen.

==================================================
5. SCREEN 3 — AI MATCH DECISION
==================================================

This is the most important pitch screen.

The judges must be able to see that the system is not simply choosing the nearest organisation.

Show three visual sections:

A. Agent Plan

Display a concise visible plan such as:

1. Read donation requirements.
2. Compare active community need.
3. Check category acceptance.
4. Check current capacity.
5. Check receiving window and route.
6. Select the best feasible destination.

B. Community Comparison

Display four organisation cards or rows.

Each organisation must show:

- current need;
- remaining capacity;
- category compatibility;
- opening status;
- estimated arrival;
- final status.

Example statuses:

- Recommended
- Excluded: unsupported category
- Excluded: insufficient capacity
- Feasible alternative

C. Final Decision

Show:

- selected organisation;
- selected quantity;
- assigned driver;
- route distance and ETA;
- concise natural-language explanation;
- “Delivery Order Created” confirmation.

The Agent explanation should be visually prominent.

Example:

“Community A is selected because it has urgent vegetable demand, sufficient current capacity, compatible receiving hours, and the shortest feasible delivery route.”

Do not show hidden chain-of-thought.

Show only the operational plan, checked facts, exclusions, and decision.

==================================================
6. SCREEN 4 — DRIVER ROUTE
==================================================

Create a mobile-style driver view alongside a larger Auckland route map.

Show:

- Woolworths Mount Eden pickup;
- Community A destination;
- food quantity;
- pickup window;
- delivery deadline;
- current ETA;
- route progress;
- delivery status timeline.

Required visible features:

- route line on Auckland map;
- moving driver marker or simulated route progress;
- pickup and destination markers;
- current load card;
- instruction card;
- “Read Instructions Aloud” button using browser SpeechSynthesis;
- “Arrived at Recipient” button.

The map can use simulated routing, but it must look credible and clearly indicate that the route is simulated.

==================================================
7. SCREEN 5 — DELIVERY CONFIRMATION
==================================================

When the driver arrives, show a clear delivery confirmation panel.

Options:

- Full acceptance
- Partial acceptance
- Rejected

For the demo, select Partial acceptance.

Show:

- planned quantity: 60 kg;
- accepted quantity input: 35 kg;
- remaining quantity calculated automatically: 25 kg;
- rejection or capacity-change reason;
- visible warning that the remaining quantity will be returned to active inventory;
- primary button: “Confirm and Rematch Remaining Food”.

The UI must make the quantity change visually obvious.

Use a before-and-after quantity display or progress bar.

==================================================
8. SCREEN 6 — AUTOMATIC REMATCH
==================================================

This is the second most important pitch screen.

The UI must visibly show the Agent reacting to a changed condition.

Show the sequence as an animated or staged timeline:

1. 35 kg accepted by Community A.
2. 25 kg returned to active inventory.
3. Community alternatives rechecked.
4. Community B excluded: unsupported category.
5. Community C excluded: only 10 kg capacity.
6. Community D selected: 30 kg capacity and open.
7. Driver route updated.
8. New delivery order created for 25 kg.

Display:

- old route;
- new route;
- updated driver destination;
- rematch explanation;
- remaining delivery deadline;
- final “All 60 kg Rescued” success state.

Example explanation:

“Community D is selected for the remaining 25 kg because it accepts vegetables, has sufficient capacity, is currently open, and can receive the delivery before 7:00 pm.”

The visual emphasis must be on recovery, not on error.

==================================================
9. COMMUNITY NEED AND CAPACITY VISIBILITY
==================================================

Need and capacity must be visually distinct throughout the UI.

Need means:
What the organisation currently wants.

Capacity means:
What it can currently receive and store.

For each community card, display both:

- Need: Vegetables — High
- Capacity: 60 kg available

A community can have demand but still be excluded because it lacks capacity.

This distinction is central to the product value and must be obvious in the pitch.

==================================================
10. AI AGENT ARCHITECTURE
==================================================

Use:

- Python 3.12+
- FastAPI
- Google ADK Python SDK
- DeepSeek API
- Pydantic v2
- SQLAlchemy 2
- SQLite
- Next.js
- React
- TypeScript
- Tailwind CSS
- Leaflet or MapLibre

Use one Agent:

FoodRedistributionAgent

Responsibility split:

DeepSeek decides.
Google ADK orchestrates.
Python tools retrieve, validate, and execute.
FastAPI exposes the workflow.
React makes the Agent visible.

DeepSeek must:

- create a concise plan;
- compare feasible recipients;
- select the destination;
- choose allocation quantity;
- choose from feasible drivers;
- react to partial acceptance;
- select a new destination;
- explain each decision.

Python tools must:

- read current donation data;
- read community need and capacity;
- validate category acceptance;
- validate storage compatibility;
- validate capacity;
- validate receiving window;
- calculate demo ETA;
- prevent duplicate allocation;
- create delivery orders;
- update remaining inventory;
- update the route.

Routine decisions require no human approval.

==================================================
11. MINIMUM REQUIRED TOOLS
==================================================

Implement only the tools required for the visible journey:

- get_donation
- list_candidate_communities
- get_community_capacity
- get_available_drivers
- calculate_route
- validate_category_acceptance
- validate_storage_compatibility
- validate_recipient_capacity
- validate_receiving_window
- validate_driver_capacity
- reserve_inventory
- reserve_recipient_capacity
- create_delivery_order
- assign_driver
- record_partial_acceptance
- release_remaining_inventory
- create_rematched_delivery
- update_driver_route

Do not create a large tool library beyond this journey.

==================================================
12. VISIBLE AGENT STATES
==================================================

The UI should show these Agent states:

- Reading donation
- Checking community demand
- Checking capacity
- Checking receiving windows
- Comparing feasible recipients
- Creating delivery order
- Assigning driver
- Delivery condition changed
- Re-evaluating alternatives
- Updating route
- Rematch complete

Use progress indicators, status chips, and a compact timeline.

Do not show technical debug logs in the primary demo interface.

==================================================
13. DESIGN DIRECTION
==================================================

The product should feel like a high-trust food redistribution control centre.

Visual direction:

- modern B2B dashboard;
- deep green primary colour;
- warm orange for risk and change;
- soft neutral background;
- bold KPI cards;
- clear status chips;
- map-driven layout;
- strong visual hierarchy;
- minimal paragraph text;
- polished transitions;
- desktop-first dashboard;
- mobile-style driver panel.

The UI should make three things instantly understandable:

1. what food is available;
2. why the Agent selected a community;
3. how the system recovers when the delivery changes.

==================================================
14. FEATURES TO KEEP BECAUSE THEY SUPPORT THE PITCH
==================================================

Keep these visible features:

- operations dashboard;
- JSON donation preview;
- Agent plan timeline;
- community comparison cards;
- exclusion reasons;
- selected-recipient explanation;
- automatic order creation confirmation;
- Auckland map;
- simulated route progress;
- driver instruction panel;
- text-to-speech button;
- partial acceptance controls;
- visible quantity calculation;
- automatic rematch timeline;
- old route versus new route;
- final rescued-food result.

==================================================
15. FEATURES TO REMOVE OR DEFER
==================================================

Do not spend MVP time on invisible or non-pitch-critical engineering.

Remove or defer:

- production authentication;
- advanced role permissions;
- PostgreSQL migration work;
- notification providers;
- email or SMS integration;
- WebSocket infrastructure unless needed for the demo animation;
- large audit-history screens;
- detailed impact analytics;
- forecasting;
- fairness optimisation;
- complex fleet optimisation;
- multi-stop route optimisation;
- external Woolworths integration;
- external charity integration;
- POS integration;
- barcode scanning;
- image processing;
- IoT monitoring;
- native mobile applications;
- production deployment infrastructure;
- extensive background jobs;
- large domain-model libraries;
- large Agent evaluation suites.

Only retain lightweight backend support needed to make the visible journey work reliably.

==================================================
16. TESTING
==================================================

Test only the core journey.

Required tests:

1. Donation submission produces valid JSON.
2. Community B is excluded because vegetables are unsupported.
3. Community C is excluded because 10 kg capacity is insufficient.
4. Community A is selected for the first 60 kg order.
5. Driver and route are created.
6. Partial acceptance records 35 kg accepted and 25 kg remaining.
7. The remaining 25 kg is not duplicated.
8. Community D is selected for the rematch.
9. Driver route updates.
10. Final delivered quantity equals 60 kg.

Include one complete end-to-end demo test.

==================================================
17. COMPLETION CRITERIA
==================================================

The MVP is complete when:

- all six screens are polished and connected;
- the complete journey can be shown in 2–3 minutes;
- the Agent decision is visible and understandable;
- community need and capacity are visually distinct;
- invalid organisations are visibly excluded with reasons;
- the first delivery order is created;
- the route is visible;
- partial acceptance can be entered;
- the remaining quantity is calculated correctly;
- the Agent automatically rematches it;
- the route visibly changes;
- the final result shows all 60 kg delivered;
- no quantity is duplicated;
- all primary buttons work;
- the frontend build passes;
- the backend starts;
- the core end-to-end test passes.

The final priority is:

A visually clear, believable, and working story of autonomous matching and recovery.
