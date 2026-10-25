/**
 * Browser acceptance — mocked inference (INFERENCE_FIXTURE on acceptance API).
 * These are real Playwright browser interactions, not HTTP-only checks.
 */
import { expect, test, type Page } from "@playwright/test";
import path from "node:path";

const SCREENSHOT_DIR = path.join("..", "docs", "screenshots");

async function generateDraft(
  page: Page,
  message: string,
  email?: string,
) {
  await page.goto("/");
  await page.getByTestId("draft-message").fill(message);
  if (email) {
    await page.getByTestId("draft-email").fill(email);
  } else {
    await page.getByTestId("draft-email").fill("");
  }
  await page.getByTestId("draft-submit").click();
  await expect(page.getByTestId("draft-success")).toBeVisible({ timeout: 60_000 });
}

test.describe("MVP browser acceptance (mocked inference)", () => {
  test("order-status draft → detail → list filter → edit → approve", async ({
    page,
  }, testInfo) => {
    const unique = `Still processing ${Date.now()}.`;
    const message = `ACCEPTANCE_ORDER_SF1001 Where is order SF-1001? ${unique}`;
    await generateDraft(page, message, "alex.rivera@example.com");
    await expect(page.getByTestId("draft-intent")).toHaveText("order_status");
    await expect(page.getByTestId("draft-outcome")).toContainText("Draft ready");
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "01-order-status-draft.png"),
      fullPage: true,
    });

    await page.getByTestId("open-review-link").click();
    await expect(page.getByTestId("detail-review-status")).toHaveText(
      "pending_review",
    );
    const detailUrl = page.url();
    expect(detailUrl).toMatch(/\/requests\/[0-9a-f-]+/);

    await page.goto("/requests");
    await page.getByTestId("filter-pending_review").click();
    await expect(page.getByTestId("request-list")).toBeVisible();
    const listHit = page.getByRole("link", { name: new RegExp(unique) });
    await expect(listHit).toBeVisible();
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "02-request-list-pending.png"),
      fullPage: true,
    });

    await listHit.click();
    await expect(page.getByTestId("editable-draft")).toBeVisible();

    const edited = "Edited order status reply for acceptance review.";
    await page.getByTestId("editable-draft").fill(edited);
    await expect(page.getByTestId("unsaved-warning")).toBeVisible();
    await expect(page.getByTestId("approve-draft")).toBeDisabled();

    await page.getByTestId("save-draft").click();
    await expect(page.getByTestId("unsaved-warning")).toHaveCount(0);
    await expect(page.getByTestId("approve-draft")).toBeEnabled();

    await page.getByTestId("approve-draft").click();
    await expect(page.getByTestId("detail-review-status")).toHaveText("approved");
    await expect(page.getByTestId("reviewed-text")).toContainText(edited);
    await expect(page.getByTestId("readonly-notice")).toBeVisible();
    await expect(page.getByTestId("editable-draft")).toHaveCount(0);
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "03-approved-detail.png"),
      fullPage: true,
    });

    testInfo.annotations.push({
      type: "note",
      description: `Approved detail URL: ${detailUrl}`,
    });
  });

  test("reject a separate request and keep it read-only", async ({ page }) => {
    const message = "ACCEPTANCE_REFUND_HANDOFF Please refund my payment.";
    await generateDraft(page, message);
    await page.getByTestId("open-review-link").click();
    await page.getByTestId("reject-draft").click();
    await expect(page.getByTestId("detail-review-status")).toHaveText("rejected");
    await expect(page.getByTestId("readonly-notice")).toBeVisible();
    await expect(page.getByTestId("save-draft")).toHaveCount(0);
  });

  test("stale revision conflict across two tabs", async ({ context }) => {
    const message =
      "ACCEPTANCE_ORDER_SF1001 Tab conflict check for SF-1001 status.";
    const page1 = await context.newPage();
    await generateDraft(page1, message, "alex.rivera@example.com");
    await page1.getByTestId("open-review-link").click();
    await expect(page1.getByTestId("editable-draft")).toBeVisible();
    const detailUrl = page1.url();

    const page2 = await context.newPage();
    await page2.goto(detailUrl);
    await expect(page2.getByTestId("editable-draft")).toBeVisible();

    await page1.getByTestId("editable-draft").fill("Saved from tab one.");
    await page1.getByTestId("save-draft").click();
    await expect(page1.getByTestId("detail-review-status")).toHaveText(
      "pending_review",
    );

    // Tab 2 still holds the old revision in React state.
    await page2.getByTestId("approve-draft").click();
    await expect(page2.getByTestId("conflict-banner")).toBeVisible();
    await expect(page2.getByTestId("conflict-banner")).toContainText(/revision|Reload/i);
  });

  test("policy answer shows supporting sources", async ({ page }) => {
    const message =
      "ACCEPTANCE_POLICY_WINDOW What is your return window for unused items?";
    await generateDraft(page, message);
    await expect(page.getByTestId("draft-intent")).toHaveText("return_policy");
    await expect(page.getByTestId("policy-sources")).toBeVisible();
    await expect(page.getByTestId("policy-sources")).toContainText(
      "eligibility-window",
    );
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "04-policy-sources.png"),
      fullPage: true,
    });
    await page.getByTestId("open-review-link").click();
    await expect(page.getByTestId("detail-policy-sources")).toBeVisible();
  });

  test("missing information when order ID absent", async ({ page }) => {
    await generateDraft(
      page,
      "ACCEPTANCE_ORDER_NO_ID Where is my package?",
      "alex.rivera@example.com",
    );
    await expect(page.getByTestId("draft-outcome")).toContainText(
      "Needs information",
    );
  });

  test("model unavailable surfaces readable error", async ({ page }) => {
    await page.goto("/");
    await page
      .getByTestId("draft-message")
      .fill("ACCEPTANCE_FORCE_OLLAMA_UNAVAILABLE ping");
    await page.getByTestId("draft-submit").click();
    await expect(page.getByTestId("draft-error")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("draft-error")).toContainText(/unavailable|Ollama/i);
  });

  test("narrow viewport keeps primary controls usable", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");
    await expect(page.getByTestId("draft-submit")).toBeVisible();
    await expect(page.getByRole("link", { name: "Review queue" })).toBeVisible();
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "05-narrow-home.png"),
      fullPage: true,
    });
  });
});
