"use client";

import { useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  Check,
  CheckCircle2,
  Clock3,
  MapPin,
  RefreshCw,
  Route,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect } from "react";

import type {
  AgentRunResponse,
  DeliveryDetailResponse,
} from "@/shared/api/client";
import {
  dashboardQueryKey,
  useAgentRunQuery,
  useDeliveryQuery,
} from "@/shared/api/queries";
import { StateBoundary } from "@/shared/ui/StateBoundary";
import { StatusChip } from "@/shared/ui/StatusChip";

export function RematchScreen({ runId }: { readonly runId: string }) {
  const search = useSearchParams();
  const deliveryId = search.get("delivery") ?? "";
  const runQuery = useAgentRunQuery(runId);
  const deliveryQuery = useDeliveryQuery(deliveryId);
  const newOrderId =
    runQuery.data?.result?.kind === "rematch"
      ? runQuery.data.result.order_refs.at(-1)
      : undefined;
  const latestDeliveryQuery = useDeliveryQuery(
    newOrderId ?? "",
    Boolean(newOrderId),
  );
  const client = useQueryClient();
  useEffect(() => {
    if (runQuery.data?.status === "succeeded")
      void client.invalidateQueries({ queryKey: dashboardQueryKey });
  }, [client, runQuery.data?.status]);
  const pending =
    runQuery.isPending ||
    deliveryQuery.isPending ||
    (Boolean(newOrderId) && latestDeliveryQuery.isPending);
  const failed =
    runQuery.isError ||
    deliveryQuery.isError ||
    latestDeliveryQuery.isError ||
    !deliveryId;
  const state = pending ? "loading" : failed ? "retryable-error" : "completed";
  return (
    <main className="page-shell">
      <StateBoundary
        state={state}
        onRetry={() => {
          void runQuery.refetch();
          void deliveryQuery.refetch();
          if (newOrderId) void latestDeliveryQuery.refetch();
        }}
      >
        {runQuery.data && deliveryQuery.data && (
          <RematchView
            run={runQuery.data}
            previous={deliveryQuery.data}
            latestInventory={latestDeliveryQuery.data?.inventory}
          />
        )}
      </StateBoundary>
    </main>
  );
}

export function RematchView({
  run,
  previous,
  latestInventory,
}: {
  readonly run: AgentRunResponse;
  readonly previous: DeliveryDetailResponse;
  readonly latestInventory?: DeliveryDetailResponse["inventory"];
}) {
  const result = run.result?.kind === "rematch" ? run.result : null;
  const decision = result?.decision;
  const inventory = latestInventory ?? result?.inventory;
  const selected = decision?.candidates.find(
    (candidate) =>
      candidate.community.community_id === decision.new_community_id,
  );
  const excluded =
    decision?.candidates.filter(
      (candidate) => candidate.status === "excluded",
    ) ?? [];
  const communityB = excluded.find(
    (candidate) =>
      candidate.community.community_id === "B" ||
      candidate.community.community_id.endsWith("-B") ||
      candidate.community.name.startsWith("Community B"),
  );
  const communityC = excluded.find(
    (candidate) =>
      candidate.community.community_id === "C" ||
      candidate.community.community_id.endsWith("-C") ||
      candidate.community.name.startsWith("Community C"),
  );
  const newOrder = result?.order_refs.at(-1);
  const steps = decision
    ? [
        `${decision.accepted_kg} kg accepted by ${previous.destination.name}`,
        `${decision.remaining_kg} kg returned to active inventory`,
        "Community alternatives rechecked",
        communityB
          ? `${communityB.community.name} excluded · ${communityB.exclusions?.[0]?.display_text ?? "Not feasible"}`
          : "First alternative checked",
        communityC
          ? `${communityC.community.name} excluded · ${communityC.exclusions?.[0]?.display_text ?? "Not feasible"}`
          : "Second alternative checked",
        `${selected?.community.name ?? "New community"} selected · ${selected?.community.remaining_capacity_kg ?? "—"} kg capacity`,
        `Driver route updated from ${decision.new_route.origin.name}`,
        `New delivery order created for ${decision.remaining_kg} kg`,
      ]
    : run.events.map((event) => event.label);
  const total = inventory
    ? inventory.available_kg +
      inventory.reserved_kg +
      inventory.in_transit_kg +
      inventory.delivered_kg
    : 0;
  const secured = inventory
    ? inventory.delivered_kg === inventory.total_kg
    : false;
  return (
    <div className="journey-stack">
      <header className="page-header">
        <div>
          <span className="eyebrow">Automatic recovery · {run.run_id}</span>
          <h1>The Agent adapts. No food is lost.</h1>
          <p>
            Changed capacity triggers an immediate, constraint-checked rematch
            of the remainder only.
          </p>
        </div>
        <StatusChip
          tone={run.transport === "replay" ? "attention" : "positive"}
        >
          {run.transport === "replay" ? "Replay mode" : "Live recovery"}
        </StatusChip>
      </header>
      <section className="rematch-grid">
        <article className="panel recovery-timeline">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Recovery timeline</span>
              <h2>Eight visible handoff steps</h2>
            </div>
            <RefreshCw size={22} />
          </div>
          <ol>
            {steps.slice(0, 8).map((step, index) => (
              <li
                key={`${index}-${step}`}
                className={index < run.events.length || decision ? "done" : ""}
              >
                <span>
                  {index < run.events.length || decision ? (
                    <Check size={15} />
                  ) : (
                    index + 1
                  )}
                </span>
                <p>{step}</p>
              </li>
            ))}
          </ol>
        </article>
        <aside className="recovery-side">
          <article className="panel route-diff">
            <div className="panel-heading">
              <div>
                <span className="eyebrow">Route recovery</span>
                <h2>Old route → new route</h2>
              </div>
              <Route size={21} />
            </div>
            <div className="route-leg old">
              <small>Original leg</small>
              <strong>{previous.order.route.origin.name}</strong>
              <span>→ {previous.order.route.destination.name}</span>
              <em>{previous.order.route.distance_km.toFixed(1)} km</em>
            </div>
            {decision ? (
              <div className="route-leg new">
                <small>Updated leg</small>
                <strong>{decision.new_route.origin.name}</strong>
                <span>→ {decision.new_route.destination.name}</span>
                <em>
                  {decision.new_route.distance_km.toFixed(1)} km · simulated
                </em>
              </div>
            ) : (
              <div className="agent-wait">Waiting for updated route…</div>
            )}
            <div className="route-proof">
              <MapPin size={15} /> New route begins at the driver&apos;s current
              location, not the store.
            </div>
          </article>
          {inventory && (
            <article
              className="panel integrity-card"
              data-testid="integrity-ledger"
            >
              <div className="panel-heading">
                <div>
                  <span className="eyebrow">Quantity integrity</span>
                  <h2>
                    {total} / {inventory.total_kg} kg accounted for
                  </h2>
                </div>
                <ShieldCheck size={22} />
              </div>
              <div className="integrity-bar">
                {(
                  [
                    "available_kg",
                    "reserved_kg",
                    "in_transit_kg",
                    "delivered_kg",
                  ] as const
                ).map((key) => (
                  <span
                    className={key}
                    key={key}
                    style={{
                      width: `${(inventory[key] / inventory.total_kg) * 100}%`,
                    }}
                  />
                ))}
              </div>
              <div className="integrity-legend">
                <span>
                  Available <strong>{inventory.available_kg}</strong>
                </span>
                <span>
                  Reserved <strong>{inventory.reserved_kg}</strong>
                </span>
                <span>
                  In transit <strong>{inventory.in_transit_kg}</strong>
                </span>
                <span>
                  Delivered <strong>{inventory.delivered_kg}</strong>
                </span>
              </div>
            </article>
          )}
        </aside>
      </section>
      {decision && (
        <section className={`success-banner ${secured ? "complete" : ""}`}>
          <div>
            <CheckCircle2 size={31} />
            <span>
              <small>{secured ? "Recovery complete" : "Rematch secured"}</small>
              <strong>
                {secured
                  ? "All 60 kg Rescued"
                  : `${decision.remaining_kg} kg rematched safely`}
              </strong>
            </span>
          </div>
          <p>{decision.explanation}</p>
          {newOrder && (
            <Link
              className="button secondary"
              href={`/deliveries/${newOrder}?returnRun=${encodeURIComponent(run.run_id)}&previousDelivery=${encodeURIComponent(previous.order.order_id)}`}
            >
              Open updated delivery <ArrowRight size={17} />
            </Link>
          )}
          <span className="deadline">
            <Clock3 size={15} /> Deadline preserved
          </span>
        </section>
      )}
    </div>
  );
}
