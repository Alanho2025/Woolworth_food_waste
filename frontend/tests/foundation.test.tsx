import { render, screen } from "@testing-library/react";

import Home from "@/app/page";

describe("platform foundation", () => {
  it("renders the empty foundation screen", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: "ok", database: "ready" }),
      }),
    );

    render(<Home />);

    expect(
      screen.getByRole("heading", { name: "Platform foundation" }),
    ).toBeInTheDocument();
  });
});
