import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { DonateForm } from "@/features/donate/DonateForm";

const { mutateAsync, push } = vi.hoisted(() => ({
  mutateAsync: vi.fn(),
  push: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("@/shared/api/queries", () => ({
  useCreateDonationMutation: () => ({
    mutateAsync,
    isPending: false,
    isError: false,
    error: null,
  }),
}));

const startedRun = {
  run_id: "RUN-001",
  donation_id: "DON-001",
  status: "queued",
  kind: "initial",
  transport: "replay",
} as const;

const expectedPreview = {
  donation_id: "DON-PREVIEW-001",
  store_id: "WW-MT-EDEN",
  pickup_window: {
    start: "2026-08-08T16:00:00+12:00",
    end: "2026-08-08T17:00:00+12:00",
  },
  items: [
    {
      item_name: "Fresh vegetables",
      category: "vegetables",
      quantity: 60,
      unit: "kg",
      storage_type: "ambient",
      delivery_deadline: "2026-08-08T19:00:00+12:00",
    },
  ],
  handling_notes: "Keep shaded and deliver in stackable produce crates.",
};

function preview(): unknown {
  return JSON.parse(screen.getByTestId("json-preview").textContent ?? "");
}

describe("DonateForm", () => {
  beforeEach(() => {
    mutateAsync.mockReset();
    push.mockReset();
    mutateAsync.mockResolvedValue({
      created: { donation: { donation_id: "DON-001" } },
      run: startedRun,
    });
  });

  it("prefills the nine required fields and renders the Requirement section 4 JSON structure", async () => {
    const user = userEvent.setup();
    render(<DonateForm />);

    await user.click(screen.getByTestId("prefill-demo"));

    await waitFor(() => expect(preview()).toEqual(expectedPreview));
    expect(screen.getByLabelText("Woolworths store")).toHaveValue("WW-MT-EDEN");
    expect(screen.getByLabelText("Food name")).toHaveValue("Fresh vegetables");
    expect(screen.getByLabelText("Category")).toHaveValue("vegetables");
    expect(screen.getByLabelText("Quantity")).toHaveValue(60);
    expect(screen.getByLabelText("Unit")).toHaveValue("kg");
    expect(screen.getByLabelText("Storage requirement")).toHaveValue("ambient");
    expect(screen.getByLabelText(/^Pickup starts/)).toHaveValue(
      "2026-08-08T16:00:00+12:00",
    );
    expect(screen.getByLabelText(/^Pickup ends/)).toHaveValue(
      "2026-08-08T17:00:00+12:00",
    );
    expect(screen.getByLabelText("Delivery deadline")).toHaveValue(
      "2026-08-08T19:00:00+12:00",
    );
    expect(screen.getByLabelText(/Notes/)).toHaveValue(
      "Keep shaded and deliver in stackable produce crates.",
    );
  });

  it("submits the validated preview through the API mutation and dispatches the real callback", async () => {
    const user = userEvent.setup();
    const onStarted = vi.fn();
    render(<DonateForm onStarted={onStarted} />);
    await user.click(screen.getByTestId("prefill-demo"));

    await user.click(
      screen.getByRole("button", { name: "Submit to AI Agent" }),
    );

    await waitFor(() =>
      expect(mutateAsync).toHaveBeenCalledWith(expectedPreview),
    );
    expect(mutateAsync).toHaveBeenCalledTimes(1);
    expect(onStarted).toHaveBeenCalledWith(startedRun);
  });

  it("navigates directly to the returned Agent match run after a successful submission", async () => {
    const user = userEvent.setup();
    render(<DonateForm />);
    await user.click(screen.getByTestId("prefill-demo"));

    await user.click(
      screen.getByRole("button", { name: "Submit to AI Agent" }),
    );

    await waitFor(() => expect(push).toHaveBeenCalledWith("/match/RUN-001"));
    expect(push).toHaveBeenCalledTimes(1);
  });

  it("blocks an invalid zero-kilogram request before the API boundary", async () => {
    const user = userEvent.setup();
    render(<DonateForm />);
    await user.click(screen.getByTestId("prefill-demo"));
    const quantity = screen.getByRole("spinbutton", { name: "Quantity" });
    await user.clear(quantity);
    await user.type(quantity, "0");

    await user.click(
      screen.getByRole("button", { name: "Submit to AI Agent" }),
    );

    expect(
      await screen.findByText("Quantity must be at least 1 kg"),
    ).toBeVisible();
    expect(mutateAsync).not.toHaveBeenCalled();
    expect(push).not.toHaveBeenCalled();
  });
});
