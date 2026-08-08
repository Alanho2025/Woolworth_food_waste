import type { LucideIcon } from "lucide-react";

interface KpiCardProps {
  readonly label: string;
  readonly value: number;
  readonly unit?: string;
  readonly note: string;
  readonly icon: LucideIcon;
  readonly tone?: "green" | "orange" | "ink";
}

export function KpiCard({
  label,
  value,
  unit,
  note,
  icon: Icon,
  tone = "green",
}: KpiCardProps) {
  return (
    <article className={`kpi-card ${tone}`}>
      <div className="kpi-head">
        <span>{label}</span>
        <Icon size={19} />
      </div>
      <div className="kpi-value">
        {value.toLocaleString("en-NZ")} {unit && <small>{unit}</small>}
      </div>
      <p>{note}</p>
    </article>
  );
}
