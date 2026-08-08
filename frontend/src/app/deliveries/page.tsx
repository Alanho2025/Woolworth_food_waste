import { StateBoundary } from "@/shared/ui/StateBoundary";
export default function DeliveriesPage() {
  return (
    <main className="page-shell">
      <StateBoundary
        state="blocked"
        title="No delivery selected"
        message="Complete an Agent match to open its driver route."
      />
    </main>
  );
}
