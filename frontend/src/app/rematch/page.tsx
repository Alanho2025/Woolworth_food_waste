import { StateBoundary } from "@/shared/ui/StateBoundary";
export default function RematchPage() {
  return (
    <main className="page-shell">
      <StateBoundary
        state="blocked"
        title="No recovery run selected"
        message="A partial handoff starts the rematch automatically."
      />
    </main>
  );
}
