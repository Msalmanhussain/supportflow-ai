/**
 * Small real-Ollama browser smoke (not fixture mode).
 * Skips when REAL_OLLAMA_SMOKE is not set or Ollama is unreachable.
 */
import { expect, test } from "@playwright/test";

const enabled = process.env.REAL_OLLAMA_SMOKE === "1";

test.describe("Real Ollama browser smoke", () => {
  test.skip(!enabled, "Set REAL_OLLAMA_SMOKE=1 with live Ollama + non-fixture API");

  test("generate a short policy draft via real model", async ({ page }) => {
    test.setTimeout(180_000);
    await page.goto("/");
    await page
      .getByTestId("draft-message")
      .fill("What is your return window for unused items?");
    await page.getByTestId("draft-submit").click();
    await expect(page.getByTestId("draft-success")).toBeVisible({
      timeout: 120_000,
    });
    await expect(page.getByTestId("draft-review-status")).toHaveText(
      "pending_review",
    );
    await expect(page.getByTestId("open-review-link")).toBeVisible();
  });
});
