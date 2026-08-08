import type { ReactNode } from "react";

type StatusTone = "positive" | "attention" | "neutral" | "info";

export function StatusChip({
  children,
  tone = "neutral",
}: {
  readonly children: ReactNode;
  readonly tone?: StatusTone;
}) {
  return <span className={`status-chip ${tone}`}>{children}</span>;
}
