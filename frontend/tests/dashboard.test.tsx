import { render, screen, within } from "@testing-library/react";

import {
  DashboardDataView,
  DashboardScreen,
} from "@/features/dashboard/DashboardScreen";
import type { DashboardResponse } from "@/shared/api/client";

const store = {
  name: "Woolworths Mount Eden",
  latitude: -36.877,
  longitude: 174.7645,
};
const communityLocation = {
  name: "Mount Roskill Community Kitchen",
  latitude: -36.9082,
  longitude: 174.7387,
};
const pickupWindow = {
  start: "2026-08-08T16:00:00+12:00",
  end: "2026-08-08T17:00:00+12:00",
};
const route = {
  origin: store,
  destination: communityLocation,
  polyline: [
    [-36.877, 174.7645],
    [-36.9082, 174.7387],
  ],
  distance_km: 5.2,
  duration_minutes: 14,
  eta: "2026-08-08T16:14:00+12:00",
  simulated: true,
} satisfies DashboardResponse["deliveries"][number]["route"];
const donation = {
  donation_id: "DON-001",
  store_id: "WW-MT-EDEN",
  store_location: store,
  pickup_window: pickupWindow,
  items: [
    {
      item_name: "Fresh vegetables (mixed)",
      category: "vegetables",
      quantity: 60,
      unit: "kg",
      storage_type: "ambient",
      delivery_deadline: "2026-08-08T19:00:00+12:00",
    },
  ],
  handling_notes: "Keep out of direct sun.",
} satisfies DashboardResponse["donations"][number];

const dashboard = {
  kpis: {
    active_surplus_kg: 60,
    matched_kg: 60,
    food_in_transit_kg: 45,
    food_at_risk_kg: 15,
    active_deliveries: 1,
    community_demand_count: 4,
    rescued_kg: 155,
    active_donations: 1,
  },
  donations: [donation],
  inventories: [
    {
      donation_id: "DON-001",
      total_kg: 60,
      available_kg: 0,
      reserved_kg: 15,
      in_transit_kg: 45,
      delivered_kg: 0,
    },
  ],
  deliveries: [
    {
      order_id: "ORD-001",
      donation_id: "DON-001",
      origin: store,
      destination_community_id: "COM-A",
      quantity_kg: 60,
      driver_id: "DRV-1",
      route,
      status: "in_transit",
      deadline: "2026-08-08T19:00:00+12:00",
      is_rematch: false,
    },
  ],
  communities: [
    {
      community_id: "COM-A",
      name: "Community A — Mount Roskill Community Kitchen",
      location: communityLocation,
      accepted_categories: ["vegetables"],
      supported_storage: ["ambient"],
      needs: [{ category: "vegetables", level: "urgent" }],
      declared_capacity_kg: 35,
      remaining_capacity_kg: 0,
      receiving_window: {
        start: "2026-08-08T08:00:00+12:00",
        end: "2026-08-08T20:00:00+12:00",
      },
      is_open: true,
    },
  ],
  drivers: [
    {
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
  ],
  agent_runs: [
    {
      run_id: "RUN-001",
      donation_id: "DON-001",
      status: "running",
      kind: "initial",
      transport: "replay",
      latest_event: {
        sequence: 0,
        state: "reading_donation",
        label: "Reading donation",
        detail: "",
        occurred_at: "2026-08-08T15:45:00+12:00",
      },
    },
  ],
  capacity_alerts: [
    {
      community_id: "COM-A",
      community_name: "Community A",
      declared_capacity_kg: 35,
      accepted_kg: 35,
      message: "Declared capacity corrected from 60 kg to 35 kg.",
    },
  ],
  urgent_donation: donation,
  active_agent_decision: {
    run_id: "RUN-001",
    donation_id: "DON-001",
    status: "running",
    kind: "initial",
    transport: "replay",
    latest_event: {
      sequence: 0,
      state: "reading_donation",
      label: "Reading donation",
      detail: "",
      occurred_at: "2026-08-08T15:45:00+12:00",
    },
  },
  active_delivery: {
    order_id: "ORD-001",
    donation_id: "DON-001",
    origin: store,
    destination_community_id: "COM-A",
    quantity_kg: 60,
    driver_id: "DRV-1",
    route,
    status: "in_transit",
    deadline: "2026-08-08T19:00:00+12:00",
    is_rematch: false,
  },
  capacity_change_highlight: {
    community_id: "COM-A",
    community_name: "Community A",
    declared_capacity_kg: 35,
    accepted_kg: 35,
    message: "Declared capacity corrected from 60 kg to 35 kg.",
  },
} satisfies DashboardResponse;

vi.mock("@/shared/api/queries", () => ({
  useDashboardQuery: () => ({
    data: dashboard,
    isPending: false,
    isError: false,
    refetch: vi.fn(),
  }),
}));

describe("Dashboard", () => {
  it("renders the pitch-required KPI, map, urgent, Agent, delivery, capacity and impact cards", () => {
    render(<DashboardDataView data={dashboard} />);

    expect(
      screen.getByRole("region", {
        name: "Network key performance indicators",
      }),
    ).toHaveTextContent("Active surplus");
    expect(screen.getByTestId("network-map")).toBeVisible();
    expect(screen.getByText(/OpenStreetMap contributors/)).toBeVisible();
    expect(screen.getByTestId("urgent-donation-card")).toHaveTextContent(
      "Fresh vegetables (mixed)",
    );
    expect(screen.getByTestId("agent-decision-card")).toHaveTextContent(
      "Reading donation",
    );
    expect(screen.getByTestId("agent-decision-card")).toHaveTextContent(
      "Replay mode · clearly labelled",
    );
    expect(screen.getByTestId("active-delivery-card")).toHaveTextContent(
      "Aroha Ngata",
    );
    expect(screen.getByTestId("active-delivery-card")).toHaveTextContent(
      "60 kg",
    );
    expect(screen.getByTestId("capacity-change-card")).toHaveTextContent(
      "Declared capacity corrected from 60 kg to 35 kg.",
    );
    expect(screen.getByText("155")).toBeVisible();
  });

  it("uses a real navigation link for the primary Create donation action", () => {
    render(<DashboardScreen />);

    const action = screen.getByTestId("create-donation");
    expect(action).toHaveAttribute("href", "/donate");
    expect(within(action).getByText("Create donation")).toBeVisible();
  });
});
