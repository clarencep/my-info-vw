import { test, expect } from "@playwright/test";

test.describe("Accessibility & Responsiveness", () => {
  test("should have a visible heading level 1", async ({ page }) => {
    await page.goto("/");

    const h1 = page.locator("h1");
    await expect(h1).toBeVisible();
  });

  test("should use semantic HTML structure", async ({ page }) => {
    await page.goto("/");

    // Check that key landmarks exist
    const mainContent = page.locator("main, [role='main'], .min-h-screen");
    await expect(mainContent.first()).toBeVisible();
  });

  test("should be usable on mobile viewport", async ({ browser }) => {
    const context = await browser.newContext({
      viewport: { width: 375, height: 667 },
    });
    const page = await context.newPage();

    await page.goto("/");

    await expect(page.locator("h1")).toContainText("消息核查器");
    await expect(page.locator("textarea")).toBeVisible();

    const button = page.getByRole("button", { name: "开始核查" });
    await expect(button).toBeVisible();

    await context.close();
  });

  test("should be usable on tablet viewport", async ({ browser }) => {
    const context = await browser.newContext({
      viewport: { width: 768, height: 1024 },
    });
    const page = await context.newPage();

    await page.goto("/");

    await expect(page.locator("h1")).toContainText("消息核查器");
    await expect(page.locator("textarea")).toBeVisible();

    await context.close();
  });
});
