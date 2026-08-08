"use client";

import {
  ArrowRight,
  Clock3,
  MapPin,
  Navigation,
  Package,
  Volume2,
} from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import type { DeliveryDetailResponse } from "@/shared/api/client";
import { useDeliveryQuery } from "@/shared/api/queries";
import { StateBoundary } from "@/shared/ui/StateBoundary";
import { StatusChip } from "@/shared/ui/StatusChip";
import { RouteMap } from "./RouteMap";

export function DriverRouteScreen({
  deliveryId,
}: {
  readonly deliveryId: string;
}) {
  const query = useDeliveryQuery(deliveryId);
  const searchParams = useSearchParams();
  const state = query.isPending
    ? "loading"
    : query.isError
      ? "retryable-error"
      : "completed";
  return (
    <main className="page-shell">
      <StateBoundary state={state} onRetry={() => void query.refetch()}>
        {query.data && (
          <DriverRouteView
            detail={query.data}
            returnRun={searchParams.get("returnRun") ?? undefined}
            previousDelivery={searchParams.get("previousDelivery") ?? undefined}
          />
        )}
      </StateBoundary>
    </main>
  );
}

export function DriverRouteView({
  detail,
  returnRun,
  previousDelivery,
}: {
  readonly detail: DeliveryDetailResponse;
  readonly returnRun?: string;
  readonly previousDelivery?: string;
}) {
  const router = useRouter();
  const [speechMessage, setSpeechMessage] = useState("");
  const item = detail.donation.items[0];
  const instruction = `Collect ${detail.order.quantity_kg} kilograms of ${item?.item_name ?? "food"} from ${detail.order.origin.name}. Deliver to ${detail.destination.name}. ${detail.donation.handling_notes}`;
  function speak() {
    if (
      !("speechSynthesis" in window) ||
      !("SpeechSynthesisUtterance" in window)
    ) {
      setSpeechMessage(
        "Speech is unavailable. Follow the written instruction below.",
      );
      return;
    }
    const utterance = new SpeechSynthesisUtterance(instruction);
    utterance.lang = "en-NZ";
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
    setSpeechMessage("Instructions are being read aloud.");
  }
  const returnQuery =
    returnRun && previousDelivery
      ? `?returnRun=${encodeURIComponent(returnRun)}&previousDelivery=${encodeURIComponent(previousDelivery)}`
      : "";
  return (
    <div className="journey-stack">
      <header className="page-header">
        <div>
          <span className="eyebrow">
            Driver route · {detail.order.order_id}
          </span>
          <h1>Next stop: {detail.destination.name}</h1>
          <p>
            Driver view keeps the load, timing and handoff action within one
            glance.
          </p>
        </div>
        <StatusChip tone="positive">
          {detail.status.replaceAll("_", " ")}
        </StatusChip>
      </header>
      <section className="driver-layout">
        <RouteMap detail={detail} />
        <aside className="driver-phone" data-testid="driver-panel">
          <div className="phone-top">
            <span>{detail.driver.name}</span>
            <StatusChip tone="positive">On route</StatusChip>
          </div>
          <div className="phone-hero">
            <Navigation size={25} />
            <div>
              <small>Current ETA</small>
              <strong>{detail.order.route.duration_minutes} min</strong>
              <span>
                {detail.order.route.distance_km.toFixed(1)} km remaining
              </span>
            </div>
          </div>
          <div className="load-card">
            <Package size={20} />
            <div>
              <small>Current load</small>
              <strong>
                {detail.order.quantity_kg} kg · {item?.item_name}
              </strong>
            </div>
          </div>
          <div className="instruction-card">
            <span className="eyebrow">Driver instruction</span>
            <p>{instruction}</p>
            <button type="button" onClick={speak}>
              <Volume2 size={17} /> Read instructions aloud
            </button>
            {speechMessage && <small role="status">{speechMessage}</small>}
          </div>
          <dl className="route-details">
            <div>
              <dt>
                <MapPin size={15} /> Pickup
              </dt>
              <dd>{detail.order.origin.name}</dd>
            </div>
            <div>
              <dt>
                <Clock3 size={15} /> Deadline
              </dt>
              <dd>
                {new Date(detail.order.deadline).toLocaleTimeString("en-NZ", {
                  hour: "numeric",
                  minute: "2-digit",
                  timeZone: "Pacific/Auckland",
                })}
              </dd>
            </div>
          </dl>
          <button
            className="button primary arrived-button"
            type="button"
            onClick={() =>
              router.push(
                `/confirm/${encodeURIComponent(detail.order.order_id)}${returnQuery}`,
              )
            }
          >
            Arrived at recipient <ArrowRight size={18} />
          </button>
          <p className="client-progression">
            Records arrival with confirmation; no backend state is fabricated
            here.
          </p>
        </aside>
      </section>
    </div>
  );
}
