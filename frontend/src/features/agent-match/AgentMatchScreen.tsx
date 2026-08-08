"use client";

import {
  ArrowRight,
  Bot,
  CheckCircle2,
  Circle,
  Clock3,
  Route,
  ShieldCheck,
  Sparkles,
  Truck,
} from "lucide-react";
import Link from "next/link";

import type { AgentRunResponse } from "@/shared/api/client";
import { useAgentRunQuery } from "@/shared/api/queries";
import { StateBoundary } from "@/shared/ui/StateBoundary";
import { StatusChip } from "@/shared/ui/StatusChip";

const plan = [
  "Read donation requirements",
  "Compare active community need",
  "Check category and storage",
  "Verify capacity",
  "Check window and route",
  "Create the best feasible order",
];

export function AgentMatchScreen({ runId }: { readonly runId: string }) {
  const query = useAgentRunQuery(runId);
  const state = query.isPending
    ? "loading"
    : query.isError
      ? "retryable-error"
      : "completed";
  return (
    <main className="page-shell">
      <StateBoundary state={state} onRetry={() => void query.refetch()}>
        {query.data && <AgentMatchView run={query.data} />}
      </StateBoundary>
    </main>
  );
}

export function AgentMatchView({ run }: { readonly run: AgentRunResponse }) {
  const result = run.result?.kind === "initial" ? run.result : null;
  const decision = result?.decision;
  const orderId = result?.order_refs[0];
  return (
    <div className="journey-stack">
      <header className="page-header">
        <div>
          <span className="eyebrow">Agent match · Run {run.run_id}</span>
          <h1>Decision, with every constraint visible</h1>
          <p>
            Operational plan and checked facts only. Hidden chain-of-thought is
            never displayed.
          </p>
        </div>
        <StatusChip
          tone={run.transport === "replay" ? "attention" : "positive"}
        >
          {run.transport === "replay" ? "Replay mode" : "Live Agent"}
        </StatusChip>
      </header>
      <section className="agent-layout">
        <article className="panel plan-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Agent plan</span>
              <h2>Six checks before allocation</h2>
            </div>
            <Bot size={22} />
          </div>
          <ol className="agent-plan">
            {plan.map((item, index) => {
              const done = index < run.events.length;
              return (
                <li key={item} className={done ? "done" : ""}>
                  {done ? <CheckCircle2 size={17} /> : <Circle size={17} />}
                  <span>{item}</span>
                </li>
              );
            })}
          </ol>
          <div className="run-status">
            <span className="network-pulse" />
            <strong>{run.events.at(-1)?.label ?? "Agent run queued"}</strong>
            <small>{run.status}</small>
          </div>
        </article>
        <section className="panel comparison-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Community comparison</span>
              <h2>Need is not capacity</h2>
            </div>
            <ShieldCheck size={22} />
          </div>
          {decision ? (
            <div className="candidate-grid">
              {decision.candidates.map((candidate) => (
                <article
                  className={`candidate-card ${candidate.status}`}
                  key={candidate.community.community_id}
                >
                  <div className="candidate-head">
                    <div>
                      <span>{candidate.community.name}</span>
                      <small>{candidate.community.location.name}</small>
                    </div>
                    <StatusChip
                      tone={
                        candidate.status === "recommended"
                          ? "positive"
                          : candidate.status === "excluded"
                            ? "attention"
                            : "neutral"
                      }
                    >
                      {candidate.status.replaceAll("_", " ")}
                    </StatusChip>
                  </div>
                  <div className="need-capacity">
                    <div className="need">
                      <small>Need</small>
                      <strong>
                        {candidate.matched_need
                          ? `${candidate.matched_need.category} · ${candidate.matched_need.level}`
                          : "No matching need"}
                      </strong>
                    </div>
                    <div className="capacity">
                      <small>Capacity</small>
                      <strong>
                        {candidate.community.remaining_capacity_kg} kg
                      </strong>
                    </div>
                  </div>
                  <dl>
                    <div>
                      <dt>Category</dt>
                      <dd>
                        {candidate.category_compatible
                          ? "Compatible"
                          : "Unsupported"}
                      </dd>
                    </div>
                    <div>
                      <dt>Open</dt>
                      <dd>
                        {candidate.community.is_open
                          ? "Receiving now"
                          : "Closed"}
                      </dd>
                    </div>
                    <div>
                      <dt>ETA</dt>
                      <dd>{candidate.route.duration_minutes} min</dd>
                    </div>
                  </dl>
                  {candidate.exclusions?.map((reason) => (
                    <p className="exclusion" key={reason.code}>
                      {reason.display_text}
                    </p>
                  ))}
                </article>
              ))}
            </div>
          ) : (
            <div className="agent-wait">
              <Sparkles size={25} />
              <h3>Agent is checking live facts</h3>
              <p>
                Candidate assessments appear progressively as the run completes.
              </p>
            </div>
          )}
        </section>
      </section>
      {decision && (
        <section className="decision-banner panel">
          <div className="decision-icon">
            <CheckCircle2 size={28} />
          </div>
          <div>
            <span className="eyebrow">
              Final decision · Delivery order created
            </span>
            <h2>
              {decision.allocated_kg} kg →{" "}
              {
                decision.candidates.find(
                  (item) =>
                    item.community.community_id ===
                    decision.selected_community_id,
                )?.community.name
              }
            </h2>
            <p>{decision.explanation}</p>
            <div className="decision-facts">
              <span>
                <Truck size={15} /> Driver {decision.driver_id}
              </span>
              <span>
                <Route size={15} /> {decision.route.distance_km.toFixed(1)} km
              </span>
              <span>
                <Clock3 size={15} /> {decision.route.duration_minutes} min ETA
              </span>
            </div>
          </div>
          {orderId && (
            <Link className="button primary" href={`/deliveries/${orderId}`}>
              Open driver route <ArrowRight size={17} />
            </Link>
          )}
        </section>
      )}
    </div>
  );
}
