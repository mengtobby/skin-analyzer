import { expect, test } from "@playwright/test";

test("settings shows the file source and scans only mocked cameras", async ({ page }) => {
  await page.route("**/api/settings/cameras", (route) => route.fulfill({
    json: { success: true, data: { cameras: [{ index: 2, width: 640, height: 480, active: false }] }, error: null },
  }));
  await page.goto("/");
  await page.getByRole("tab", { name: "Settings", exact: true }).click();
  await expect(page.getByText("Video file", { exact: true })).toBeVisible();
  await expect(page.getByRole("radio", { name: "Camera 2 · 640×480" })).toBeVisible();
  await expect(page).toHaveURL(/#settings$/);
  await page.reload();
  await expect(page.getByRole("tab", { name: "Settings", exact: true })).toHaveAttribute("aria-selected", "true");
});
