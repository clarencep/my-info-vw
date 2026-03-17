import { test, expect } from "@playwright/test";

test.describe("Home Page", () => {
  test("should display the page title and description", async ({ page }) => {
    await page.goto("/");

    await expect(page.locator("h1")).toContainText("消息核查器");
    await expect(page.getByText("AI 驱动的事实核查")).toBeVisible();
  });

  test("should have the correct HTML lang attribute", async ({ page }) => {
    await page.goto("/");

    const lang = await page.getAttribute("html", "lang");
    expect(lang).toBe("zh-CN");
  });

  test("should have the correct page title in metadata", async ({ page }) => {
    await page.goto("/");

    await expect(page).toHaveTitle(/消息核查器/);
  });

  test("should render the textarea input", async ({ page }) => {
    await page.goto("/");

    const textarea = page.locator("textarea");
    await expect(textarea).toBeVisible();
    await expect(textarea).toHaveAttribute(
      "placeholder",
      "输入需要核查的消息..."
    );
  });

  test("should display the submit button as disabled when input is empty", async ({
    page,
  }) => {
    await page.goto("/");

    const button = page.getByRole("button", { name: "开始核查" });
    await expect(button).toBeDisabled();
  });

  test("should enable the submit button when text is entered", async ({
    page,
  }) => {
    await page.goto("/");

    const textarea = page.locator("textarea");
    await textarea.fill("这是一条测试消息");

    const button = page.getByRole("button", { name: "开始核查" });
    await expect(button).toBeEnabled();
  });

  test("should show character count as text is typed", async ({ page }) => {
    await page.goto("/");

    const textarea = page.locator("textarea");
    await textarea.fill("测试消息");

    await expect(page.getByText("4 字符")).toBeVisible();
  });

  test("should clear character count when input is cleared", async ({
    page,
  }) => {
    await page.goto("/");

    const textarea = page.locator("textarea");
    await textarea.fill("测试消息");
    await textarea.clear();

    await expect(page.getByText("0 字符")).toBeVisible();
  });
});
