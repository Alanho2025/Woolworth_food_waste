import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AgentMatchView } from "@/features/agent-match/AgentMatchScreen";
import { DeliveryConfirmationView } from "@/features/delivery-confirmation/DeliveryConfirmationScreen";
import { DriverRouteView } from "@/features/driver-route/DriverRouteScreen";
import { RematchView } from "@/features/rematch/RematchScreen";
import type {
  AgentRunResponse,
  ConfirmDeliveryResponse,
  DeliveryDetailResponse,
} from "@/shared/api/client";

const { mutateAsync, push } = vi.hoisted(() => ({
  mutateAsync: vi.fn(),
  push: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("@/shared/api/queries", () => ({
  useConfirmDeliveryMutation: () => ({
    mutateAsync,
    isPending: false,
    isError: false,
    error: null,
  }),
}));

const store = {
  name: "Woolworths Mount Eden",
  latitude: -36.877,
  longitude: 174.7645,
};
const locations = {
  A: {
    name: "Mount Roskill Community Kitchen",
    latitude: -36.9082,
    longitude: 174.7387,
  },
  B: {
    name: "Ponsonby Family Support Centre",
    latitude: -36.8555,
    longitude: 174.746,
  },
  C: {
    name: "Onehunga Foodbank",
    latitude: -36.923,
    longitude: 174.783,
  },
  D: {
    name: "Ellerslie Community Pantry",
    latitude: -36.8985,
    longitude: 174.809,
  },
};

function route(
  origin: typeof store,
  destination: typeof store,
  durationMinutes: number,
) {
  return {
    origin,
    destination,
    polyline: [
      [origin.latitude, origin.longitude],
      [destination.latitude, destination.longitude],
    ] as [number, number][],
    distance_km: durationMinutes / 2,
    duration_minutes: durationMinutes,
    eta: "2026-08-08T16:15:00+12:00",
    simulated: true,
  };
}

function community(
  id: "A" | "B" | "C" | "D",
  capacity: number,
  need: "urgent" | "high" | "medium",
) {
  return {
    community_id: `COM-${id}`,
    name: `Community ${id} — ${locations[id].name}`,
    location: locations[id],
    accepted_categories: (id === "B" ? ["dairy"] : ["vegetables"]) as (
      | "dairy"
      | "vegetables"
    )[],
    supported_storage: ["ambient"] as "ambient"[],
    needs: [
      {
        category: id === "B" ? ("dairy" as const) : ("vegetables" as const),
        level: need,
      },
    ],
    declared_capacity_kg: capacity,
    remaining_capacity_kg: capacity,
    receiving_window: {
      start: "2026-08-08T08:00:00+12:00",
      end: "2026-08-08T20:00:00+12:00",
    },
    is_open: true,
  };
}

const communities = {
  A: community("A", 60, "urgent"),
  B: community("B", 80, "high"),
  C: community("C", 10, "high"),
  D: community("D", 30, "medium"),
};

const donation = {
  donation_id: "DON-001",
  store_id: "WW-MT-EDEN",
  store_location: store,
  pickup_window: {
    start: "2026-08-08T16:00:00+12:00",
    end: "2026-08-08T17:00:00+12:00",
  },
  items: [
    {
      item_name: "Fresh vegetables (mixed)",
      category: "vegetables" as const,
      quantity: 60,
      unit: "kg" as const,
      storage_type: "ambient" as const,
      delivery_deadline: "2026-08-08T19:00:00+12:00",
    },
  ],
  handling_notes: "Keep out of direct sun.",
};

function candidate(
  id: "A" | "B" | "C" | "D",
  status: "recommended" | "feasible_alternative" | "excluded",
  duration: number,
  exclusion?: {
    code: "RECIPIENT_CATEGORY_UNSUPPORTED" | "RECIPIENT_CAPACITY_EXCEEDED";
    display_text: string;
  },
) {
  return {
    community: communities[id],
    matched_need: communities[id].needs[0]!,
    category_compatible: id !== "B",
    storage_compatible: true,
    capacity_sufficient: id !== "C",
    window_open_on_arrival: true,
    within_deadline: true,
    route: route(store, locations[id], duration),
    status,
    exclusions: exclusion ? [exclusion] : [],
  };
}

const initialRun = {
  run_id: "RUN-INITIAL",
  donation_id: "DON-001",
  status: "succeeded",
  kind: "initial",
  transport: "replay",
  started_at: "2026-08-08T15:45:00+12:00",
  completed_at: "2026-08-08T15:46:00+12:00",
  events: [
    {
      sequence: 1,
      state: "reading_donation",
      label: "Reading donation",
      detail: "",
      occurred_at: "2026-08-08T15:45:00+12:00",
    },
  ],
  result: {
    kind: "initial",
    decision: {
      donation_id: "DON-001",
      selected_community_id: "COM-A",
      allocated_kg: 60,
      driver_id: "DRV-1",
      route: route(store, locations.A, 10),
      explanation:
        "Community A has urgent vegetable demand, sufficient capacity, compatible hours and the shortest simulated route.",
      candidates: [
        candidate("B", "excluded", 9, {
          code: "RECIPIENT_CATEGORY_UNSUPPORTED",
          display_text: "Does not accept vegetables",
        }),
        candidate("A", "recommended", 10),
        candidate("C", "excluded", 14, {
          code: "RECIPIENT_CAPACITY_EXCEEDED",
          display_text: "Only 10 kg capacity; cannot receive 60 kg",
        }),
        candidate("D", "feasible_alternative", 16),
      ],
    },
    inventory: {
      donation_id: "DON-001",
      total_kg: 60,
      available_kg: 0,
      reserved_kg: 60,
      in_transit_kg: 0,
      delivered_kg: 0,
    },
    order_refs: ["ORD-A"],
  },
} satisfies AgentRunResponse;

const previous = {
  order: {
    order_id: "ORD-A",
    donation_id: "DON-001",
    origin: store,
    destination_community_id: "COM-A",
    quantity_kg: 60,
    driver_id: "DRV-1",
    route: route(store, locations.A, 10),
    status: "partially_accepted",
    deadline: "2026-08-08T19:00:00+12:00",
    is_rematch: false,
  },
  donation,
  driver: {
    driver_id: "DRV-1",
    name: "Aroha Ngata",
    start_location: {
      name: "Newmarket Depot",
      latitude: -36.87,
      longitude: 174.777,
    },
    vehicle_capacity_kg: 80,
    is_available: false,
  },
  destination: communities.A,
  inventory: {
    donation_id: "DON-001",
    total_kg: 60,
    available_kg: 25,
    reserved_kg: 0,
    in_transit_kg: 0,
    delivered_kg: 35,
  },
  status: "partially_accepted",
  status_timeline: [
    {
      sequence: 0,
      status: "created",
      label: "created",
      occurred_at: "2026-08-08T15:45:00+12:00",
    },
    {
      sequence: 1,
      status: "partially_accepted",
      label: "partially accepted",
      occurred_at: "2026-08-08T16:20:00+12:00",
    },
  ],
} satisfies DeliveryDetailResponse;

function rematchRun(delivered = 35): AgentRunResponse {
  const reserved = 60 - delivered;
  return {
    run_id: "RUN-REMATCH",
    donation_id: "DON-001",
    status: "succeeded",
    kind: "rematch",
    transport: "replay",
    started_at: "2026-08-08T16:21:00+12:00",
    completed_at: "2026-08-08T16:22:00+12:00",
    events: [
      {
        sequence: 1,
        state: "delivery_condition_changed",
        label: "Delivery condition changed",
        detail: "25 kg requires rematch",
        occurred_at: "2026-08-08T16:21:00+12:00",
      },
      {
        sequence: 2,
        state: "re_evaluating_alternatives",
        label: "Re-evaluating alternatives",
        detail: "",
        occurred_at: "2026-08-08T16:21:10+12:00",
      },
      {
        sequence: 3,
        state: "updating_route",
        label: "Updating route",
        detail: "",
        occurred_at: "2026-08-08T16:21:20+12:00",
      },
      {
        sequence: 4,
        state: "rematch_complete",
        label: "Rematch complete",
        detail: "",
        occurred_at: "2026-08-08T16:21:30+12:00",
      },
    ],
    result: {
      kind: "rematch",
      decision: {
        donation_id: "DON-001",
        original_community_id: "COM-A",
        accepted_kg: 35,
        remaining_kg: 25,
        new_community_id: "COM-D",
        new_route: route(locations.A, locations.D, 12),
        explanation:
          "Community D can receive the remaining 25 kg before the deadline.",
        candidates: [
          candidate("B", "excluded", 11, {
            code: "RECIPIENT_CATEGORY_UNSUPPORTED",
            display_text: "Does not accept vegetables",
          }),
          candidate("C", "excluded", 8, {
            code: "RECIPIENT_CAPACITY_EXCEEDED",
            display_text: "Only 10 kg capacity; cannot receive 25 kg",
          }),
          {
            ...candidate("D", "recommended", 12),
            route: route(locations.A, locations.D, 12),
          },
        ],
      },
      inventory: {
        donation_id: "DON-001",
        total_kg: 60,
        available_kg: 0,
        reserved_kg: reserved,
        in_transit_kg: 0,
        delivered_kg: delivered,
      },
      order_refs: ["ORD-D"],
    },
  };
}

describe("P6/P7 visible journey", () => {
  beforeEach(() => {
    push.mockReset();
    mutateAsync.mockReset();
  });

  it("shows all four candidate ETAs and the exact B/C exclusion facts without raw reasoning", () => {
    render(<AgentMatchView run={initialRun} />);

    for (const id of ["A", "B", "C", "D"] as const) {
      const card = screen.getByText(communities[id].name).closest("article");
      expect(card).not.toBeNull();
      expect(within(card as HTMLElement).getByText(/min$/)).toBeVisible();
    }
    expect(screen.getByText("Does not accept vegetables")).toBeVisible();
    expect(
      screen.getByText("Only 10 kg capacity; cannot receive 60 kg"),
    ).toBeVisible();
    expect(
      screen.queryByText("SECRET MODEL SCRATCHPAD"),
    ).not.toBeInTheDocument();
  });

  it("labels the simulated route, calls speech synthesis, and navigates on arrival", async () => {
    const user = userEvent.setup();
    const speak = vi.spyOn(window.speechSynthesis, "speak");
    const cancel = vi.spyOn(window.speechSynthesis, "cancel");
    render(<DriverRouteView detail={previous} />);

    expect(screen.getByText("Simulated route")).toBeVisible();
    expect(screen.getByTestId("driver-panel")).toHaveTextContent("60 kg");
    await user.click(
      screen.getByRole("button", { name: "Read instructions aloud" }),
    );
    expect(cancel).toHaveBeenCalledTimes(1);
    expect(speak).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("status")).toHaveTextContent(
      "Instructions are being read aloud.",
    );

    await user.click(
      screen.getByRole("button", { name: "Arrived at recipient" }),
    );
    expect(push).toHaveBeenCalledWith("/confirm/ORD-A");
    speak.mockRestore();
    cancel.mockRestore();
  });

  it("previews 35/25 then makes one authoritative confirmation and follows its rematch run", async () => {
    const user = userEvent.setup();
    mutateAsync.mockResolvedValue({
      delivery: previous.order,
      outcome: "partial",
      planned_kg: 60,
      accepted_kg: 35,
      remaining_kg: 25,
      corrected_community: { ...communities.A, declared_capacity_kg: 35 },
      inventory: {
        donation_id: "DON-001",
        total_kg: 60,
        available_kg: 25,
        reserved_kg: 0,
        in_transit_kg: 0,
        delivered_kg: 35,
      },
      rematch_run_id: "RUN-REMATCH",
    } satisfies ConfirmDeliveryResponse);
    render(<DeliveryConfirmationView detail={previous} />);

    expect(screen.getByText("35 kg", { selector: "strong" })).toBeVisible();
    expect(screen.getByText("25 kg", { selector: "strong" })).toBeVisible();
    await user.click(
      screen.getByRole("button", {
        name: "Confirm and rematch remaining food",
      }),
    );

    await waitFor(() =>
      expect(mutateAsync).toHaveBeenCalledWith({
        outcome: "partial",
        accepted_kg: 35,
        reason: "Recipient capacity changed at handoff",
      }),
    );
    expect(mutateAsync).toHaveBeenCalledTimes(1);
    expect(push).toHaveBeenCalledWith("/rematch/RUN-REMATCH?delivery=ORD-A");
  });

  it("renders eight B/C-aware rematch steps and only claims all rescued at delivered 60", () => {
    const { rerender } = render(
      <RematchView run={rematchRun()} previous={previous} />,
    );

    const timeline = screen.getByRole("heading", {
      name: "Eight visible handoff steps",
    }).parentElement?.parentElement?.parentElement;
    expect(timeline).not.toBeNull();
    expect(
      within(timeline as HTMLElement).getAllByRole("listitem"),
    ).toHaveLength(8);
    expect(timeline).toHaveTextContent("Community B");
    expect(timeline).toHaveTextContent("Does not accept vegetables");
    expect(timeline).toHaveTextContent("Community C");
    expect(timeline).toHaveTextContent("Only 10 kg capacity");
    expect(timeline).toHaveTextContent(
      "Driver route updated from Mount Roskill Community Kitchen",
    );
    const ledger = screen.getByTestId("integrity-ledger");
    expect(ledger).toHaveTextContent("60 / 60 kg accounted for");
    expect(ledger).toHaveTextContent("Reserved 25");
    expect(ledger).toHaveTextContent("Delivered 35");
    expect(screen.queryByText("All 60 kg Rescued")).not.toBeInTheDocument();
    expect(screen.getByText("25 kg rematched safely")).toBeVisible();

    expect(
      screen.getByRole("link", { name: "Open updated delivery" }),
    ).toHaveAttribute(
      "href",
      "/deliveries/ORD-D?returnRun=RUN-REMATCH&previousDelivery=ORD-A",
    );

    rerender(
      <RematchView
        run={rematchRun()}
        previous={previous}
        latestInventory={{
          donation_id: "DON-001",
          total_kg: 60,
          available_kg: 0,
          reserved_kg: 0,
          in_transit_kg: 0,
          delivered_kg: 60,
        }}
      />,
    );
    expect(screen.getByTestId("integrity-ledger")).toHaveTextContent(
      "Delivered 60",
    );
    expect(screen.getByText("All 60 kg Rescued")).toBeVisible();
  });

  it("returns from the final D confirmation to the authoritative rematch run", async () => {
    const user = userEvent.setup();
    const replacement = {
      ...previous,
      order: {
        ...previous.order,
        order_id: "ORD-D",
        origin: locations.A,
        destination_community_id: "COM-D",
        quantity_kg: 25,
        route: route(locations.A, locations.D, 12),
        status: "driver_assigned" as const,
        is_rematch: true,
      },
      destination: communities.D,
      inventory: {
        donation_id: "DON-001",
        total_kg: 60,
        available_kg: 0,
        reserved_kg: 25,
        in_transit_kg: 0,
        delivered_kg: 35,
      },
      status: "driver_assigned" as const,
    } satisfies DeliveryDetailResponse;
    mutateAsync.mockResolvedValue({
      delivery: { ...replacement.order, status: "completed" },
      outcome: "full",
      planned_kg: 25,
      accepted_kg: 25,
      remaining_kg: 0,
      corrected_community: communities.D,
      inventory: {
        donation_id: "DON-001",
        total_kg: 60,
        available_kg: 0,
        reserved_kg: 0,
        in_transit_kg: 0,
        delivered_kg: 60,
      },
      rematch_run_id: null,
    } satisfies ConfirmDeliveryResponse);
    render(
      <DeliveryConfirmationView
        detail={replacement}
        returnRun="RUN-REMATCH"
        previousDelivery="ORD-A"
      />,
    );

    await user.click(screen.getByRole("radio", { name: /full/i }));
    await user.click(
      screen.getByRole("button", {
        name: "Confirm and rematch remaining food",
      }),
    );

    await waitFor(() =>
      expect(mutateAsync).toHaveBeenCalledWith({
        outcome: "full",
        accepted_kg: 25,
        reason: "Recipient capacity changed at handoff",
      }),
    );
    expect(mutateAsync).toHaveBeenCalledTimes(1);
    expect(push).toHaveBeenCalledWith("/rematch/RUN-REMATCH?delivery=ORD-A");
  });
});
