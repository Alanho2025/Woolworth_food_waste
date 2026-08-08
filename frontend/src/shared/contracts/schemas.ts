/**
 * Runtime validation of everything that crosses the network boundary.
 *
 * clean_code_spec 8.5 requires API responses to be generated from or validated
 * against the backend contracts. The OpenAPI artefact does not exist yet, so
 * this is the validation half: every response is parsed before it reaches a
 * component, and a shape change in the backend surfaces as a typed, visible
 * error instead of `undefined` rendering as a blank cell on the pitch screen.
 *
 * The schemas are derived from `./core.ts`, which mirrors
 * `backend/app/contracts/core.py`. `satisfies` ties each schema back to its
 * interface so the two cannot drift silently.
 */

import { z } from "zod";

import {
  AGENT_STATES,
  CANDIDATE_STATUSES,
  DELIVERY_STATUSES,
  ERROR_CODES,
  FOOD_CATEGORIES,
  NEED_LEVELS,
  STORAGE_TYPES,
} from "./core";
import { ACCEPTANCE_OUTCOMES } from "./api";

export const foodCategorySchema = z.enum(FOOD_CATEGORIES);
export const storageTypeSchema = z.enum(STORAGE_TYPES);
export const needLevelSchema = z.enum(NEED_LEVELS);
export const deliveryStatusSchema = z.enum(DELIVERY_STATUSES);
export const candidateStatusSchema = z.enum(CANDIDATE_STATUSES);
export const agentStateSchema = z.enum(AGENT_STATES);
export const errorCodeSchema = z.enum(ERROR_CODES);
export const acceptanceOutcomeSchema = z.enum(ACCEPTANCE_OUTCOMES);

/** Whole kilograms. Never a float — the integrity invariant is undecidable
 *  under IEEE-754 (docs/phase_review_findings.md R-17). */
const kilograms = z.number().int().min(0);
const positiveKilograms = z.number().int().positive();

const isoTimestamp = z.string().min(1);

export const locationSchema = z.object({
  name: z.string(),
  latitude: z.number().min(-90).max(90),
  longitude: z.number().min(-180).max(180),
});

export const timeWindowSchema = z.object({
  start: isoTimestamp,
  end: isoTimestamp,
});

export const routeLegSchema = z.object({
  origin: locationSchema,
  destination: locationSchema,
  polyline: z.array(z.tuple([z.number(), z.number()])).min(2),
  distance_km: z.number().nonnegative(),
  duration_minutes: z.number().int().nonnegative(),
  eta: isoTimestamp,
  simulated: z.boolean(),
});

export const foodItemSchema = z.object({
  item_name: z.string().min(1),
  category: foodCategorySchema,
  quantity: positiveKilograms,
  unit: z.string().min(1),
  storage_type: storageTypeSchema,
  delivery_deadline: isoTimestamp,
});

export const donationRequestSchema = z.object({
  donation_id: z.string().min(1),
  store_id: z.string().min(1),
  store_location: locationSchema,
  pickup_window: timeWindowSchema,
  items: z.array(foodItemSchema).min(1),
  handling_notes: z.string(),
});

export const donationInventorySchema = z
  .object({
    donation_id: z.string().min(1),
    total_kg: positiveKilograms,
    available_kg: kilograms,
    reserved_kg: kilograms,
    in_transit_kg: kilograms,
    delivered_kg: kilograms,
  })
  .refine(
    (inv) =>
      inv.available_kg +
        inv.reserved_kg +
        inv.in_transit_kg +
        inv.delivered_kg ===
      inv.total_kg,
    {
      // AGENTS_FoodFlow.md 8.4 calls this blocker-level. If the backend ever
      // ships an unbalanced ledger, the UI refuses to draw the integrity bar
      // rather than drawing a bar that quietly does not sum to 60.
      message:
        "Quantity integrity violated: available + reserved + in_transit + delivered must equal total_kg",
    },
  );

export const communityNeedSchema = z.object({
  category: foodCategorySchema,
  level: needLevelSchema,
});

export const communityOrganisationSchema = z.object({
  community_id: z.string().min(1),
  name: z.string().min(1),
  location: locationSchema,
  accepted_categories: z.array(foodCategorySchema),
  supported_storage: z.array(storageTypeSchema),
  needs: z.array(communityNeedSchema),
  remaining_capacity_kg: kilograms,
  receiving_window: timeWindowSchema,
  is_open: z.boolean(),
});

export const driverSchema = z.object({
  driver_id: z.string().min(1),
  name: z.string().min(1),
  start_location: locationSchema,
  vehicle_capacity_kg: positiveKilograms,
  is_available: z.boolean(),
});

export const exclusionReasonSchema = z.object({
  code: errorCodeSchema,
  display_text: z.string().min(1),
});

export const candidateAssessmentSchema = z.object({
  community: communityOrganisationSchema,
  matched_need: communityNeedSchema.nullable(),
  category_compatible: z.boolean(),
  storage_compatible: z.boolean(),
  capacity_sufficient: z.boolean(),
  window_open_on_arrival: z.boolean(),
  within_deadline: z.boolean(),
  // Required, not optional: R-18. An excluded candidate still carries a route,
  // so every card on the comparison table can show an ETA.
  route: routeLegSchema,
  status: candidateStatusSchema,
  exclusions: z.array(exclusionReasonSchema),
});

export const allocationDecisionSchema = z.object({
  donation_id: z.string().min(1),
  selected_community_id: z.string().min(1),
  allocated_kg: positiveKilograms,
  driver_id: z.string().min(1),
  route: routeLegSchema,
  explanation: z.string().min(1),
  candidates: z.array(candidateAssessmentSchema).min(1),
});

export const rematchDecisionSchema = z.object({
  donation_id: z.string().min(1),
  original_community_id: z.string().min(1),
  accepted_kg: kilograms,
  remaining_kg: positiveKilograms,
  new_community_id: z.string().min(1),
  new_route: routeLegSchema,
  explanation: z.string().min(1),
  candidates: z.array(candidateAssessmentSchema).min(1),
});

export const deliveryOrderSchema = z.object({
  order_id: z.string().min(1),
  donation_id: z.string().min(1),
  origin: locationSchema,
  destination_community_id: z.string().min(1),
  quantity_kg: positiveKilograms,
  driver_id: z.string().min(1),
  route: routeLegSchema,
  status: deliveryStatusSchema,
  deadline: isoTimestamp,
  is_rematch: z.boolean(),
});

export const agentStateEventSchema = z.object({
  sequence: z.number().int().nonnegative(),
  state: agentStateSchema,
  label: z.string().min(1),
  detail: z.string(),
  occurred_at: isoTimestamp,
});

export const agentRunSchema = z.object({
  run_id: z.string().min(1),
  donation_id: z.string().min(1),
  events: z.array(agentStateEventSchema),
  is_complete: z.boolean(),
  error_code: errorCodeSchema.nullable(),
});

// --- API envelopes (see ./api.ts — these shapes are assumed, not mirrored) ---

export const matchRunStartedSchema = z.object({
  run_id: z.string().min(1),
  donation_id: z.string().min(1),
});

export const confirmDeliveryResultSchema = z.object({
  order_id: z.string().min(1),
  accepted_kg: kilograms,
  remaining_kg: kilograms,
  rematch_run_id: z.string().min(1).nullable(),
  inventory: donationInventorySchema,
});

export const deliveryDetailSchema = z.object({
  order: deliveryOrderSchema,
  driver: driverSchema,
  destination: communityOrganisationSchema,
  inventory: donationInventorySchema,
});

export const dashboardSnapshotSchema = z.object({
  generated_at: isoTimestamp,
  kpi: z.object({
    active_surplus_kg: kilograms,
    matched_kg: kilograms,
    in_transit_kg: kilograms,
    at_risk_kg: kilograms,
    active_deliveries: z.number().int().nonnegative(),
    rescued_kg_total: kilograms,
  }),
  store_locations: z.array(locationSchema),
  communities: z.array(communityOrganisationSchema),
  drivers: z.array(driverSchema),
  urgent_donation: z
    .object({
      donation_id: z.string().min(1),
      store_name: z.string().min(1),
      summary: z.string().min(1),
      quantity_kg: positiveKilograms,
      deadline: isoTimestamp,
      minutes_to_deadline: z.number().int(),
    })
    .nullable(),
  agent_decision: z
    .object({
      donation_id: z.string().min(1),
      headline: z.string().min(1),
      selected_community_name: z.string().min(1),
      allocated_kg: positiveKilograms,
      decided_at: isoTimestamp,
    })
    .nullable(),
  active_delivery: z
    .object({
      order_id: z.string().min(1),
      driver_name: z.string().min(1),
      origin_name: z.string().min(1),
      destination_name: z.string().min(1),
      quantity_kg: positiveKilograms,
      status: deliveryStatusSchema,
      eta: isoTimestamp,
    })
    .nullable(),
  capacity_alert: z
    .object({
      community_id: z.string().min(1),
      community_name: z.string().min(1),
      previous_capacity_kg: kilograms,
      current_capacity_kg: kilograms,
      released_kg: kilograms,
      raised_at: isoTimestamp,
    })
    .nullable(),
});

export const apiErrorBodySchema = z.object({
  code: errorCodeSchema,
  detail: z.string(),
});
