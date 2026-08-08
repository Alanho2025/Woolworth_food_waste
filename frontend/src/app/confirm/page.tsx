import { StateBoundary } from "@/shared/ui/StateBoundary";
export default function ConfirmPage() {
  return (
    <main className="page-shell">
      <StateBoundary
        state="blocked"
        title="No handoff selected"
        message="Use Arrived at recipient from a live driver route."
      />
    </main>
  );
}
