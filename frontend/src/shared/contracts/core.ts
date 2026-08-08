/**
 * TypeScript mirror of `backend/app/contracts/core.py`.
 *
 * That Pydantic module is THE data contract and is authoritative. Every name,
 * enum member, and nesting level below is copied from it verbatim. If the two
 * ever disagree, the Python file wins and this file is wrong.
 *
 * Four concepts are kept deliberately separate and must not be collapsed
 * (Requirement.md 9, AGENTS_FoodFlow.md 8.2):
 *
 *   Need        what a community currently wants
 *   Capacity    what it can currently receive and store
 *   Eligibility whether hard constraints allow a delivery
 *   Decision    which eligible option the Agent selected, and why
 *
 * A community can have urgent need and still be ineligible for lack of
 * capacity. That distinction is the product's value proposition, and the UI
 * renders the two with different visual treatments for exactly that reason.
 *
 * NOTE ON GENERATION (clean_code_spec 8.5): the spec prefers a client generated
 * from `backend/contracts/openapi.json`. That artefact does not exist yet — the
 * backend is being built in parallel and has shipped only the contracts module.
 * These types are therefore hand-mirrored AND validated at runtime by the Zod
 * schemas in `./schemas.ts`, which is the other half of what 8.5 permits
 * ("generated from OR validated against backend contracts"). When the OpenAPI
 * artefact lands, replace this file with generated output; the Zod boundary
 * stays either way, because it is what catches drift.
 */

// ---------------------------------------------------------------------------
// Enumerations
// ---------------------------------------------------------------------------

export const FOOD_CATEGORIES = [
  "vegetables",
  "fruit",
  "bakery",
  "dairy",
  "meat",
  "ambient_grocery",
] as const;
export type FoodCategory = (typeof FOOD_CATEGORIES)[number];

export const STORAGE_TYPES = ["ambient", "chilled", "frozen"] as const;
export type StorageType = (typeof STORAGE_TYPES)[number];

export const NEED_LEVELS = ["none", "low", "medium", "high", "urgent"] as const;
export type NeedLevel = (typeof NEED_LEVELS)[number];

export const DELIVERY_STATUSES = [
  "created",
  "driver_assigned",
  "in_transit",
  "arrived",
  "partially_accepted",
  "completed",
  "rejected",
] as const;
export type DeliveryStatus = (typeof DELIVERY_STATUSES)[number];

/** Final label shown on each community card on the Agent Match screen. */
export const CANDIDATE_STATUSES = [
  "recommended",
  "feasible_alternative",
  "excluded",
] as const;
export type CandidateStatus = (typeof CANDIDATE_STATUSES)[number];

/**
 * The eleven visible states of Requirement.md 12.
 *
 * The backend persists these incrementally as the run proceeds. The UI polls
 * and reveals them as they arrive — it never waits for completion and replays,
 * which would put every visible state on screen after the decision it exists to
 * explain (docs/phase_review_findings.md R-2).
 */
export const AGENT_STATES = [
  "reading_donation",
  "checking_community_demand",
  "checking_capacity",
  "checking_receiving_windows",
  "comparing_feasible_recipients",
  "creating_delivery_order",
  "assigning_driver",
  "delivery_condition_changed",
  "re_evaluating_alternatives",
  "updating_route",
  "rematch_complete",
] as const;
export type AgentState = (typeof AGENT_STATES)[number];

/** Mirrors `backend/app/domain/errors.py::ErrorCode`. */
export const ERROR_CODES = [
  "RECIPIENT_CATEGORY_UNSUPPORTED",
  "RECIPIENT_CAPACITY_EXCEEDED",
  "STORAGE_INCOMPATIBLE",
  "RECEIVING_WINDOW_CLOSED",
  "DELIVERY_DEADLINE_MISSED",
  "DRIVER_CAPACITY_EXCEEDED",
  "DRIVER_UNAVAILABLE",
  "RECIPIENT_DECLINED_THIS_DONATION",
  "INSUFFICIENT_INVENTORY",
  "DUPLICATE_ALLOCATION",
  "QUANTITY_INTEGRITY_VIOLATION",
  "INVALID_STATE_TRANSITION",
  "AGENT_OUTPUT_INVALID",
  "AGENT_STEP_LIMIT_REACHED",
  "AGENT_TIMEOUT",
  "TOOL_VALIDATION_FAILED",
  "TOOL_NOT_FOUND",
  "TOOL_TIMEOUT",
  "TOOL_RATE_LIMITED",
  "TOOL_INVALID_RESULT",
  "TOOL_INTERNAL_FAILURE",
  "DONATION_INVALID",
  "NOT_FOUND",
] as const;
export type ErrorCode = (typeof ERROR_CODES)[number];

// ---------------------------------------------------------------------------
// Geography
// ---------------------------------------------------------------------------

export interface Location {
  name: string;
  latitude: number;
  longitude: number;
}

/** ISO-8601 timestamps as delivered by FastAPI. Never parsed with a literal
 *  UTC offset — the offset lives in the string (docs/assumption_audit.md C-1). */
export interface TimeWindow {
  start: string;
  end: string;
}

/** `[latitude, longitude]`, matching `list[tuple[float, float]]` in core.py. */
export type PolylinePoint = readonly [number, number];

/** A simulated route. Never presented as real routing (AGENTS_FoodFlow.md 2). */
export interface RouteLeg {
  origin: Location;
  destination: Location;
  polyline: PolylinePoint[];
  distance_km: number;
  duration_minutes: number;
  eta: string;
  simulated: boolean;
}

// ---------------------------------------------------------------------------
// Donation
// ---------------------------------------------------------------------------

export interface FoodItem {
  item_name: string;
  category: FoodCategory;
  /** Integer kilograms, strictly positive (backend/app/domain/quantity.py). */
  quantity: number;
  unit: string;
  storage_type: StorageType;
  delivery_deadline: string;
}

export interface DonationRequest {
  donation_id: string;
  store_id: string;
  store_location: Location;
  pickup_window: TimeWindow;
  items: FoodItem[];
  handling_notes: string;
}

/**
 * The quantity ledger for one donation.
 *
 * The four components must always sum to `total_kg`. The UI renders them as a
 * stacked bar, which is the visible proof clean_code_spec 8.4 requires.
 */
export interface DonationInventory {
  donation_id: string;
  total_kg: number;
  available_kg: number;
  reserved_kg: number;
  in_transit_kg: number;
  delivered_kg: number;
}

// ---------------------------------------------------------------------------
// Community
// ---------------------------------------------------------------------------

/** What the organisation WANTS. Distinct from what it can receive. */
export interface CommunityNeed {
  category: FoodCategory;
  level: NeedLevel;
}

export interface CommunityOrganisation {
  community_id: string;
  name: string;
  location: Location;
  accepted_categories: FoodCategory[];
  supported_storage: StorageType[];
  needs: CommunityNeed[];
  /** What it can currently RECEIVE AND STORE, as opposed to what it wants. */
  remaining_capacity_kg: number;
  receiving_window: TimeWindow;
  is_open: boolean;
}

// ---------------------------------------------------------------------------
// Driver
// ---------------------------------------------------------------------------

export interface Driver {
  driver_id: string;
  name: string;
  start_location: Location;
  vehicle_capacity_kg: number;
  is_available: boolean;
}

// ---------------------------------------------------------------------------
// Agent decision surface
// ---------------------------------------------------------------------------

export interface ExclusionReason {
  code: ErrorCode;
  /** Shown verbatim on the community card. The UI never rewrites this string —
   *  the exact wording is a correctness requirement (assumption_audit C-2). */
  display_text: string;
}

/**
 * One community's complete fact set, plus its eligibility label.
 *
 * Every displayable fact is computed for EVERY candidate, including ones that
 * already failed a hard constraint — so `route` (and therefore the ETA) is
 * always present, even on excluded cards (phase_review_findings R-18).
 */
export interface CandidateAssessment {
  community: CommunityOrganisation;
  matched_need: CommunityNeed | null;
  category_compatible: boolean;
  storage_compatible: boolean;
  capacity_sufficient: boolean;
  window_open_on_arrival: boolean;
  within_deadline: boolean;
  route: RouteLeg;
  status: CandidateStatus;
  exclusions: ExclusionReason[];
}

export interface AllocationDecision {
  donation_id: string;
  selected_community_id: string;
  allocated_kg: number;
  driver_id: string;
  route: RouteLeg;
  /** Concise operational explanation. Never chain-of-thought. */
  explanation: string;
  candidates: CandidateAssessment[];
}

export interface RematchDecision {
  donation_id: string;
  original_community_id: string;
  accepted_kg: number;
  remaining_kg: number;
  new_community_id: string;
  new_route: RouteLeg;
  explanation: string;
  candidates: CandidateAssessment[];
}

export interface DeliveryOrder {
  order_id: string;
  donation_id: string;
  /** Explicit location, NOT implicitly the donating store. The rematched leg
   *  departs from Community A where the driver is already standing
   *  (docs/assumption_audit.md C-4). */
  origin: Location;
  destination_community_id: string;
  quantity_kg: number;
  driver_id: string;
  route: RouteLeg;
  status: DeliveryStatus;
  deadline: string;
  is_rematch: boolean;
}

/** One visible step of an Agent run. */
export interface AgentStateEvent {
  sequence: number;
  state: AgentState;
  label: string;
  detail: string;
  occurred_at: string;
}

export interface AgentRun {
  run_id: string;
  donation_id: string;
  events: AgentStateEvent[];
  is_complete: boolean;
  /** Set only on failure; a run never reports success with an error present. */
  error_code: ErrorCode | null;
}

export interface AuditEvent {
  event_id: string;
  donation_id: string;
  action: string;
  detail: string;
  occurred_at: string;
  succeeded: boolean;
}
