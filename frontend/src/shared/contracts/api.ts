/**
 * API envelope types — the request/response shapes that wrap the core
 * contracts.
 *
 * IMPORTANT, and deliberately in its own file: **nothing here comes from
 * `backend/app/contracts/core.py`.** These are the shapes the six screens need
 * from the endpoint list in `docs/implementation_phases.md` P4, which had not
 * been written when this frontend was built. They are the frontend's stated
 * expectation of the API, kept separate from the mirrored contracts so that
 * drift is visible rather than blended in.
 *
 * Everything in `./core.ts` is authoritative and copied. Everything here is
 * ASSUMED and must be reconciled against P4's real routes.
 */

import type {
  AllocationDecision,
  CommunityOrganisation,
  DeliveryOrder,
  DonationInventory,
  DonationRequest,
  Driver,
  ErrorCode,
  RematchDecision,
} from "./core";

/** How a recipient responded on arrival (Requirement.md 7). */
export const ACCEPTANCE_OUTCOMES = ["full", "partial", "rejected"] as const;
export type AcceptanceOutcome = (typeof ACCEPTANCE_OUTCOMES)[number];

/** `POST /donations` body. The donation_id is minted by the backend. */
export interface CreateDonationBody {
  store_id: string;
  store_location: { name: string; latitude: number; longitude: number };
  pickup_window: { start: string; end: string };
  items: DonationRequest["items"];
  handling_notes: string;
}

/**
 * `POST /donations/{id}/match` — returns IMMEDIATELY with a run id.
 * The run itself is async; the UI polls `GET /agent-runs/{run_id}`
 * (docs/phase_review_findings.md R-2).
 */
export interface MatchRunStarted {
  run_id: string;
  donation_id: string;
}

/** `POST /deliveries/{order_id}/confirm` body. */
export interface ConfirmDeliveryBody {
  outcome: AcceptanceOutcome;
  /** Integer kilograms actually taken by the recipient. */
  accepted_kg: number;
  reason: string;
}

/**
 * `POST /deliveries/{order_id}/confirm` response.
 *
 * The rematch run is started by the SAME request that records the acceptance —
 * one click, no second confirmation (docs/phase_review_findings.md R-24).
 * `rematch_run_id` is null only when nothing remains to place.
 */
export interface ConfirmDeliveryResult {
  order_id: string;
  accepted_kg: number;
  remaining_kg: number;
  rematch_run_id: string | null;
  inventory: DonationInventory;
}

/** `GET /donations/{id}/allocation` */
export type AllocationResponse = AllocationDecision;

/** `GET /donations/{id}/rematch` */
export type RematchResponse = RematchDecision;

/**
 * `GET /dashboard` — everything Requirement.md 3 puts on the opening screen,
 * in one round trip. The Dashboard refetches this so it reflects state produced
 * later in the journey (docs/phase_review_findings.md R-12).
 */
export interface DashboardSnapshot {
  generated_at: string;
  kpi: {
    active_surplus_kg: number;
    matched_kg: number;
    in_transit_kg: number;
    at_risk_kg: number;
    active_deliveries: number;
    /** Cumulative, including seeded historical deliveries, so the opening
     *  slide never reads 0 kg (docs/phase_review_findings.md R-21). */
    rescued_kg_total: number;
  };
  store_locations: DonationRequest["store_location"][];
  communities: CommunityOrganisation[];
  drivers: Driver[];
  urgent_donation: UrgentDonationCard | null;
  agent_decision: AgentDecisionCard | null;
  active_delivery: ActiveDeliveryCard | null;
  capacity_alert: CapacityAlertCard | null;
}

export interface UrgentDonationCard {
  donation_id: string;
  store_name: string;
  summary: string;
  quantity_kg: number;
  deadline: string;
  minutes_to_deadline: number;
}

export interface AgentDecisionCard {
  donation_id: string;
  headline: string;
  selected_community_name: string;
  allocated_kg: number;
  decided_at: string;
}

export interface ActiveDeliveryCard {
  order_id: string;
  driver_name: string;
  origin_name: string;
  destination_name: string;
  quantity_kg: number;
  status: DeliveryOrder["status"];
  eta: string;
}

export interface CapacityAlertCard {
  community_id: string;
  community_name: string;
  previous_capacity_kg: number;
  current_capacity_kg: number;
  released_kg: number;
  raised_at: string;
}

/** FastAPI error body — a typed code, never a bare message (clean_code_spec 6.3). */
export interface ApiErrorBody {
  code: ErrorCode;
  detail: string;
}

/** Everything the /route screen needs for one delivery, in one round trip. */
export interface DeliveryDetail {
  order: DeliveryOrder;
  driver: Driver;
  destination: CommunityOrganisation;
  inventory: DonationInventory;
}
