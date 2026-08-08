"use client";

import { useEffect, useState } from "react";

type HealthResponse = {
  status: string;
  database: string;
};

const backendUrl =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    fetch(`${backendUrl}/health`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Backend returned ${response.status}`);
        }
        return (await response.json()) as HealthResponse;
      })
      .then(setHealth)
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") {
          return;
        }
        setError("Backend is not reachable yet.");
      });

    return () => controller.abort();
  }, []);

  return (
    <main>
      <h1>Platform foundation</h1>
      <p>The application is ready for the first product feature.</p>
      <section className="status" aria-live="polite">
        {health && (
          <p>
            Backend: {health.status}; database: {health.database}.
          </p>
        )}
        {error && <p className="status-error">{error}</p>}
        {!health && !error && <p>Checking backend readiness…</p>}
      </section>
    </main>
  );
}
