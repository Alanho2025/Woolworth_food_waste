import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";

import { StateBoundary, type BoundaryState } from "@/shared/ui/StateBoundary";

function RetryHarness() {
  const [state, setState] = useState<BoundaryState>("retryable-error");
  return (
    <StateBoundary state={state} onRetry={() => setState("completed")}>
      <p>Recovered live content</p>
    </StateBoundary>
  );
}

describe("StateBoundary", () => {
  it.each([
    ["loading", "Connecting to the Auckland network"],
    ["blocked", "This workflow is not available yet"],
    ["retryable-error", "Live service is temporarily unavailable"],
  ] satisfies ReadonlyArray<readonly [BoundaryState, string]>)(
    "renders the visible %s state",
    (state, heading) => {
      render(<StateBoundary state={state} />);

      expect(screen.getByTestId(`state-${state}`)).toBeVisible();
      expect(screen.getByRole("heading", { name: heading })).toBeVisible();
    },
  );

  it("renders completed children instead of a status placeholder", () => {
    render(
      <StateBoundary state="completed">
        <p>Live dashboard content</p>
      </StateBoundary>,
    );

    expect(screen.getByText("Live dashboard content")).toBeVisible();
    expect(screen.queryByText("Live system status")).not.toBeInTheDocument();
  });

  it("dispatches the real retry handler and leaves the error state", async () => {
    const user = userEvent.setup();
    render(<RetryHarness />);

    await user.click(screen.getByRole("button", { name: "Retry connection" }));

    expect(screen.getByText("Recovered live content")).toBeVisible();
    expect(
      screen.queryByTestId("state-retryable-error"),
    ).not.toBeInTheDocument();
  });
});
