import { ArrowLeft, LockKeyhole } from "lucide-react";
import Link from "next/link";

export function ComingSoon({
  step,
  title,
}: {
  readonly step: string;
  readonly title: string;
}) {
  return (
    <main className="page-shell">
      <section className="coming-soon panel">
        <span className="state-icon">
          <LockKeyhole size={25} />
        </span>
        <span className="eyebrow">Journey {step}</span>
        <h1>{title}</h1>
        <p>
          This route is reserved for the next implementation phase. No workflow
          result has been fabricated.
        </p>
        <Link className="button secondary" href="/">
          <ArrowLeft size={17} /> Return to control centre
        </Link>
      </section>
    </main>
  );
}
