import { expect, test, type Locator, type Page } from "@playwright/test";

async function expectCandidateEta(page: Page, communityName: RegExp) {
  const card = page.locator("article.candidate-card").filter({
    has: page.getByText(communityName),
  });
  await expect(card).toBeVisible();
  await expect(card.getByText(/\d+ min/)).toBeVisible();
  return card;
}

async function expectLedgerValue(
  ledger: Locator,
  label: string,
  value: number,
) {
  await expect(
    ledger.locator(".integrity-legend span").filter({ hasText: label }),
  ).toContainText(`${value}`);
}

test("six-screen 60 kg rescue and automatic 35/25 recovery", async ({
  page,
}) => {
  test.setTimeout(45_000);

  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Food rescue control centre" }),
  ).toBeVisible();
  await expect(page.getByTestId("network-map")).toBeVisible();
  await page.getByTestId("create-donation").click();

  await expect(
    page.getByRole("heading", { name: "Create a food donation" }),
  ).toBeVisible();
  await page.getByTestId("prefill-demo").click();
  await expect(page.getByTestId("json-preview")).toContainText(
    '"quantity": 60',
  );
  await expect(page.getByTestId("json-preview")).toContainText(
    '"category": "vegetables"',
  );
  await page.getByRole("button", { name: "Submit to AI Agent" }).click();

  await expect(page).toHaveURL(/\/match\/RUN-[A-Z0-9]+$/);
  await expect(
    page.getByRole("heading", {
      name: "Decision, with every constraint visible",
    }),
  ).toBeVisible();
  const a = await expectCandidateEta(page, /Community A/);
  const b = await expectCandidateEta(page, /Community B/);
  const c = await expectCandidateEta(page, /Community C/);
  await expectCandidateEta(page, /Community D/);
  await expect(a).toContainText("recommended");
  await expect(a).toContainText("60 kg");
  await expect(b).toContainText("Does not accept vegetables");
  await expect(c).toContainText(
    "Insufficient capacity for a single-destination allocation (10 kg available, 60 kg required)",
  );
  await expect(page.getByText(/60 kg → Community A/)).toBeVisible();
  await page.getByRole("link", { name: "Open driver route" }).click();

  await expect(page.getByText("Simulated route")).toBeVisible();
  await expect(page.getByTestId("driver-panel")).toContainText("Aroha Ngata");
  await expect(page.getByTestId("driver-panel")).toContainText("60 kg");
  await page.getByRole("button", { name: "Read instructions aloud" }).click();
  await expect(page.getByRole("status")).toContainText(
    "Instructions are being read aloud.",
  );
  await page.getByRole("button", { name: "Arrived at recipient" }).click();

  await expect(
    page.getByRole("heading", { name: "Confirm what was accepted" }),
  ).toBeVisible();
  await expect(page.getByText("35 kg", { exact: true })).toBeVisible();
  await expect(page.getByText("25 kg", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Confirm and rematch remaining food" })
    .click();

  await expect(page).toHaveURL(/\/rematch\/RUN-[A-Z0-9]+\?delivery=ORD-/);
  await expect(
    page.getByRole("heading", { name: "Eight visible handoff steps" }),
  ).toBeVisible();
  const timeline = page.locator("article.recovery-timeline");
  await expect(timeline.locator("li")).toHaveCount(8);
  await expect(timeline).toContainText("35 kg accepted");
  await expect(timeline).toContainText("25 kg returned to active inventory");
  await expect(timeline).toContainText("Community B");
  await expect(timeline).toContainText("Does not accept vegetables");
  await expect(timeline).toContainText("Community C");
  await expect(timeline).toContainText("10 kg available, 25 kg required");
  await expect(timeline).toContainText("Community D");
  await expect(timeline).toContainText(
    "Driver route updated from Mount Roskill Community Kitchen",
  );
  const ledger = page.getByTestId("integrity-ledger");
  await expect(ledger).toContainText("60 / 60 kg accounted for");
  await expectLedgerValue(ledger, "Available", 0);
  await expectLedgerValue(ledger, "Reserved", 25);
  await expectLedgerValue(ledger, "In transit", 0);
  await expectLedgerValue(ledger, "Delivered", 35);
  await expect(page.getByText("All 60 kg Rescued")).toHaveCount(0);

  await page.getByRole("link", { name: "Open updated delivery" }).click();
  await expect(page).toHaveURL(
    /\/deliveries\/ORD-.+\?returnRun=RUN-.+&previousDelivery=ORD-/,
  );
  await expect(page.getByText("Simulated route")).toBeVisible();
  await expect(page.getByTestId("driver-panel")).toContainText("25 kg");
  await expect(page.getByTestId("driver-panel")).toContainText(
    "Mount Roskill Community Kitchen",
  );
  await page.getByRole("button", { name: "Arrived at recipient" }).click();
  await page.getByRole("radio", { name: /full/i }).click();
  await page
    .getByRole("button", { name: "Confirm and rematch remaining food" })
    .click();

  await expect(page).toHaveURL(/\/rematch\/RUN-.+\?delivery=ORD-/);
  await expect(page.getByText("All 60 kg Rescued")).toBeVisible();
  const finalLedger = page.getByTestId("integrity-ledger");
  await expect(finalLedger).toContainText("60 / 60 kg accounted for");
  await expectLedgerValue(finalLedger, "Available", 0);
  await expectLedgerValue(finalLedger, "Reserved", 0);
  await expectLedgerValue(finalLedger, "In transit", 0);
  await expectLedgerValue(finalLedger, "Delivered", 60);
});
