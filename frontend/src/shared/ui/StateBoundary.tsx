import {
  AlertCircle,
  LoaderCircle,
  LockKeyhole,
  RefreshCw,
} from "lucide-react";
import type { ReactNode } from "react";

export type BoundaryState =
  | "loading"
  | "blocked"
  | "retryable-error"
  | "completed";

interface StateBoundaryProps {
  readonly state: BoundaryState;
  readonly children?: ReactNode;
  readonly title?: string;
  readonly message?: string;
  readonly onRetry?: () => void;
}

export function StateBoundary({
  state,
  children,
  title,
  message,
  onRetry,
}: StateBoundaryProps) {
  if (state === "completed") return <>{children}</>;

  const content = {
    loading: {
      icon: LoaderCircle,
      heading: title ?? "Connecting to the Auckland network",
      copy:
        message ?? "Loading live donations, drivers and community capacity.",
    },
    blocked: {
      icon: LockKeyhole,
      heading: title ?? "This workflow is not available yet",
      copy: message ?? "Complete the preceding journey step to continue.",
    },
    "retryable-error": {
      icon: AlertCircle,
      heading: title ?? "Live service is temporarily unavailable",
      copy:
        message ??
        "No demo data has been substituted. Start the backend service, then retry.",
    },
  }[state];
  const Icon = content.icon;

  return (
    <section
      className={`state-panel ${state}`}
      aria-live="polite"
      data-testid={`state-${state}`}
    >
      <span className="state-icon">
        <Icon size={25} className={state === "loading" ? "spin" : ""} />
      </span>
      <div>
        <span className="eyebrow">Live system status</span>
        <h2>{content.heading}</h2>
        <p>{content.copy}</p>
      </div>
      {state === "retryable-error" && onRetry && (
        <button className="button secondary" type="button" onClick={onRetry}>
          <RefreshCw size={17} /> Retry connection
        </button>
      )}
    </section>
  );
}
