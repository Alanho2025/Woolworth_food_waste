import { expect, test } from "@playwright/test";

test("P0 browser gate launches a real browser and evaluates a rendered page", async ({
  page,
}) => {
  await page.setContent(`
    <main>
      <h1>Kind KAI</h1>
      <p data-testid="gate-status">P0 browser gate is running</p>
    </main>
  `);

  await expect(page.getByRole("heading", { name: "Kind KAI" })).toBeVisible();
  await expect(page.getByTestId("gate-status")).toHaveText(
    "P0 browser gate is running",
  );
});
