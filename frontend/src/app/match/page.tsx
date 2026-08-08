import { StateBoundary } from "@/shared/ui/StateBoundary";
export default function MatchIndexPage() {
  return (
    <main className="page-shell">
      <StateBoundary
        state="blocked"
        title="Start with a donation"
        message="Submit the donation form to create a traceable Agent run."
      />
    </main>
  );
}
