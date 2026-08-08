"use client";

import {
  AlertTriangle,
  ArrowRight,
  Bot,
  CircleGauge,
  Clock3,
  PackageCheck,
  Route,
  Scale,
  Truck,
  Users,
} from "lucide-react";
import Link from "next/link";

import type { DashboardResponse } from "@/shared/api/client";
import { useDashboardQuery } from "@/shared/api/queries";
import { KpiCard } from "@/shared/ui/KpiCard";
import { StateBoundary } from "@/shared/ui/StateBoundary";
import { StatusChip } from "@/shared/ui/StatusChip";

import { NetworkMap } from "./NetworkMap";

function shortTime(value: string) {
  return new Intl.DateTimeFormat("en-NZ", {
    hour: "numeric",
    minute: "2-digit",
    timeZone: "Pacific/Auckland",
  }).format(new Date(value));
}

function displayName(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function DashboardScreen() {
  const query = useDashboardQuery();
  const state = query.isPending
    ? "loading"
    : query.isError
      ? "retryable-error"
      : "completed";

  return (
    <main className="page-shell">
      <header className="page-header">
        <div>
          <span className="eyebrow">Saturday · 08 August · Live shift</span>
          <h1>Food rescue control centre</h1>
          <p>
            One operational view of surplus, community need and every active
            handoff.
          </p>
        </div>
        <Link
          className="button primary"
          href="/donate"
          data-testid="create-donation"
        >
          <span>Create donation</span>
          <ArrowRight size={18} />
        </Link>
      </header>
      <StateBoundary state={state} onRetry={() => void query.refetch()}>
        {query.data && <DashboardDataView data={query.data} />}
      </StateBoundary>
    </main>
  );
}

export function DashboardDataView({
  data,
}: {
  readonly data: DashboardResponse;
}) {
  const urgentItem = data.urgent_donation?.items[0];
  const activeDelivery = data.active_delivery;
  const activeDestination = data.communities.find(
    (community) =>
      community.community_id === activeDelivery?.destination_community_id,
  );
  const activeDriver = data.drivers.find(
    (driver) => driver.driver_id === activeDelivery?.driver_id,
  );
  const agent = data.active_agent_decision;
  const alert = data.capacity_change_highlight;

  return (
    <div className="dashboard-stack">
      <section
        className="kpi-grid"
        aria-label="Network key performance indicators"
      >
        <KpiCard
          label="Active surplus"
          value={data.kpis.active_surplus_kg}
          unit="kg"
          note={`${data.kpis.active_donations} donations ready`}
          icon={Scale}
        />
        <KpiCard
          label="Matched food"
          value={data.kpis.matched_kg}
          unit="kg"
          note="Reserved for community partners"
          icon={PackageCheck}
          tone="ink"
        />
        <KpiCard
          label="In transit"
          value={data.kpis.food_in_transit_kg}
          unit="kg"
          note={`${data.kpis.active_deliveries} active deliveries`}
          icon={Truck}
          tone="green"
        />
        <KpiCard
          label="At risk"
          value={data.kpis.food_at_risk_kg}
          unit="kg"
          note="Needs attention before deadline"
          icon={AlertTriangle}
          tone="orange"
        />
      </section>

      <section className="dashboard-main-grid">
        <NetworkMap data={data} />
        <aside className="signal-stack">
          <article
            className="signal-card urgent"
            data-testid="urgent-donation-card"
          >
            <div className="signal-top">
              <StatusChip tone="attention">Urgent donation</StatusChip>
              <Clock3 size={18} />
            </div>
            {data.urgent_donation && urgentItem ? (
              <>
                <h3>{urgentItem.item_name}</h3>
                <p>{data.urgent_donation.store_location.name}</p>
                <div className="signal-metric">
                  <strong>{urgentItem.quantity}</strong>
                  <span>
                    kg available
                    <br />
                    deadline {shortTime(urgentItem.delivery_deadline)}
                  </span>
                </div>
                <Link href="/donate">
                  Open donation <ArrowRight size={15} />
                </Link>
              </>
            ) : (
              <p>No urgent donations right now.</p>
            )}
          </article>
          <article className="signal-card" data-testid="agent-decision-card">
            <div className="signal-top">
              <StatusChip tone="info">Agent decision</StatusChip>
              <Bot size={18} />
            </div>
            {agent ? (
              <>
                <h3>
                  {agent.kind === "rematch"
                    ? "Recovery in progress"
                    : "Matching in progress"}
                </h3>
                <p>{agent.latest_event?.label ?? "Agent run queued"}</p>
                <div className="agent-row">
                  <CircleGauge size={19} />
                  <div>
                    <strong>{displayName(agent.status)}</strong>
                    <span>
                      {agent.transport === "replay"
                        ? "Replay mode · clearly labelled"
                        : "Live DeepSeek run"}
                    </span>
                  </div>
                </div>
              </>
            ) : (
              <p>No active Agent decision.</p>
            )}
          </article>
        </aside>
      </section>

      <section className="operations-row">
        <article className="operation-card" data-testid="active-delivery-card">
          <div className="operation-icon">
            <Truck size={21} />
          </div>
          <div className="operation-copy">
            <span className="eyebrow">Active delivery</span>
            <h3>
              {activeDelivery
                ? `${activeDriver?.name ?? "Assigned driver"} → ${activeDestination?.name ?? "Community"}`
                : "No delivery in motion"}
            </h3>
            <p>
              {activeDelivery
                ? `${activeDelivery.quantity_kg} kg · ETA ${shortTime(activeDelivery.route.eta)}`
                : "New routes will appear here."}
            </p>
          </div>
          {activeDelivery && (
            <StatusChip tone="positive">
              {displayName(activeDelivery.status)}
            </StatusChip>
          )}
        </article>
        <article
          className="operation-card change"
          data-testid="capacity-change-card"
        >
          <div className="operation-icon">
            <Users size={21} />
          </div>
          <div className="operation-copy">
            <span className="eyebrow">Capacity change</span>
            <h3>{alert?.community_name ?? "Partner capacity stable"}</h3>
            <p>{alert?.message ?? "No changes need action."}</p>
          </div>
          {alert && (
            <strong className="capacity-number">
              {alert.declared_capacity_kg} kg
            </strong>
          )}
        </article>
        <article className="impact-card">
          <div>
            <span className="eyebrow">Collective impact</span>
            <h3>
              {data.kpis.rescued_kg.toLocaleString("en-NZ")} <small>kg</small>
            </h3>
            <p>Food rescued across completed deliveries</p>
          </div>
          <Route size={28} />
        </article>
      </section>
    </div>
  );
}
