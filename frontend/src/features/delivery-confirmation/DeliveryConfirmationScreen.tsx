"use client";

import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  PackageOpen,
  RotateCcw,
} from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import type { DeliveryDetailResponse } from "@/shared/api/client";
import {
  useConfirmDeliveryMutation,
  useDeliveryQuery,
} from "@/shared/api/queries";
import { StateBoundary } from "@/shared/ui/StateBoundary";

type Outcome = "full" | "partial" | "rejected";

export function DeliveryConfirmationScreen({
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
          <DeliveryConfirmationView
            detail={query.data}
            returnRun={searchParams.get("returnRun") ?? undefined}
            previousDelivery={searchParams.get("previousDelivery") ?? undefined}
          />
        )}
      </StateBoundary>
    </main>
  );
}

export function DeliveryConfirmationView({
  detail,
  returnRun,
  previousDelivery,
}: {
  readonly detail: DeliveryDetailResponse;
  readonly returnRun?: string;
  readonly previousDelivery?: string;
}) {
  const router = useRouter();
  const mutation = useConfirmDeliveryMutation(detail.order.order_id);
  const [outcome, setOutcome] = useState<Outcome>(
    detail.order.is_rematch ? "full" : "partial",
  );
  const [accepted, setAccepted] = useState(
    detail.order.is_rematch
      ? detail.order.quantity_kg
      : Math.min(35, detail.order.quantity_kg),
  );
  const [reason, setReason] = useState("Recipient capacity changed at handoff");
  const previewRemaining = Math.max(0, detail.order.quantity_kg - accepted);
  async function confirm() {
    try {
      const result = await mutation.mutateAsync({
        outcome,
        accepted_kg: accepted,
        reason,
      });
      if (result.rematch_run_id)
        router.push(
          `/rematch/${encodeURIComponent(result.rematch_run_id)}?delivery=${encodeURIComponent(detail.order.order_id)}`,
        );
      else if (returnRun && previousDelivery)
        router.push(
          `/rematch/${encodeURIComponent(returnRun)}?delivery=${encodeURIComponent(previousDelivery)}`,
        );
      else router.push("/");
    } catch {
      // React Query exposes the API message through mutation.error below.
    }
  }
  return (
    <div className="journey-stack">
      <header className="page-header">
        <div>
          <span className="eyebrow">Recipient handoff</span>
          <h1>Confirm what was accepted</h1>
          <p>
            The backend remains authoritative for every quantity transition and
            any rematch.
          </p>
        </div>
      </header>
      <section className="confirmation-layout">
        <article className="panel confirmation-panel">
          <div
            className="acceptance-options"
            role="radiogroup"
            aria-label="Acceptance outcome"
          >
            {(["full", "partial", "rejected"] as const).map((value) => (
              <button
                type="button"
                role="radio"
                aria-checked={outcome === value}
                className={outcome === value ? "selected" : ""}
                key={value}
                onClick={() => {
                  setOutcome(value);
                  if (value === "full") setAccepted(detail.order.quantity_kg);
                  if (value === "rejected") setAccepted(0);
                }}
              >
                {value === "full" ? (
                  <CheckCircle2 size={19} />
                ) : value === "partial" ? (
                  <PackageOpen size={19} />
                ) : (
                  <RotateCcw size={19} />
                )}
                <span>
                  {value}
                  <small>
                    {value === "partial" ? "Demo path" : "Record outcome"}
                  </small>
                </span>
              </button>
            ))}
          </div>
          <label className="field">
            <span>
              Accepted quantity <small>whole kilograms</small>
            </span>
            <input
              type="number"
              min="0"
              max={detail.order.quantity_kg}
              step="1"
              value={accepted}
              disabled={outcome !== "partial"}
              onChange={(event) =>
                setAccepted(
                  Math.max(
                    0,
                    Math.min(
                      detail.order.quantity_kg,
                      Number(event.target.value),
                    ),
                  ),
                )
              }
            />
          </label>
          <label className="field">
            <span>Reason for change</span>
            <textarea
              rows={3}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            />
          </label>
          <div className="return-warning">
            <AlertCircle size={19} />
            <div>
              <strong>
                {previewRemaining} kg will return to active inventory
              </strong>
              <p>
                This is a form preview only. The response ledger below the
                workflow is server-authoritative.
              </p>
            </div>
          </div>
          {mutation.isError && (
            <div className="inline-error" role="alert">
              {mutation.error.message}
            </div>
          )}
          <button
            className="button primary confirm-rematch"
            type="button"
            disabled={mutation.isPending}
            onClick={() => void confirm()}
          >
            {mutation.isPending
              ? "Confirming…"
              : "Confirm and rematch remaining food"}
            <ArrowRight size={18} />
          </button>
        </article>
        <aside className="quantity-proof panel">
          <span className="eyebrow">Before and after</span>
          <h2>Quantity change</h2>
          <div className="quantity-before">
            <span>Planned</span>
            <strong>{detail.order.quantity_kg} kg</strong>
          </div>
          <div className="quantity-bar">
            <span
              style={{
                width: `${detail.order.quantity_kg ? (accepted / detail.order.quantity_kg) * 100 : 0}%`,
              }}
            />
          </div>
          <div className="quantity-split">
            <div>
              <small>Accepted</small>
              <strong>{accepted} kg</strong>
            </div>
            <div>
              <small>Returns</small>
              <strong>{previewRemaining} kg</strong>
            </div>
          </div>
          <p>
            One click records acceptance and automatically starts the remainder
            rematch. There is no second approval step.
          </p>
        </aside>
      </section>
    </div>
  );
}
