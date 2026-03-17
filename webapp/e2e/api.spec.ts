import { test, expect } from "@playwright/test";

test.describe("API /api/check", () => {
  test("should return 400 when message is empty", async ({ request }) => {
    const response = await request.post("/api/check", {
      data: { message: "" },
    });

    expect(response.status()).toBe(400);
    const body = await response.json();
    expect(body.error).toBeTruthy();
  });

  test("should return 400 when message is missing", async ({ request }) => {
    const response = await request.post("/api/check", {
      data: {},
    });

    expect(response.status()).toBe(400);
  });
});
